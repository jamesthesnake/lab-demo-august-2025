"""
LLM Service
Handles natural language to code conversion and intelligent code generation
"""

import os
import json
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, asdict
import openai
from openai import AsyncOpenAI
import anthropic
from anthropic import AsyncAnthropic
import tiktoken
import re

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"  # For future local model support

@dataclass
class CodeGeneration:
    """Generated code with metadata"""
    code: str
    explanation: str
    confidence: float
    libraries_used: List[str]
    estimated_runtime: str
    warnings: List[str]

@dataclass
class AnalysisContext:
    """Context for code generation"""
    session_id: str
    previous_code: List[str]
    available_files: List[str]
    variables_in_scope: Dict[str, str]
    installed_packages: List[str]
    execution_history: List[Dict[str, Any]]

class LLMService:
    """
    Service for handling LLM interactions and code generation
    """
    
    # System prompts for different tasks
    SYSTEM_PROMPTS = {
        "data_analysis": """You are an expert data scientist assistant that generates Python code for data analysis.

IMPORTANT RULES:
1. Generate ONLY executable Python code, no explanations or markdown
2. Always import necessary libraries at the beginning
3. Handle errors gracefully with try-except blocks when appropriate
4. Create visualizations when requested or when they would be helpful
5. Save all plots to '/workspace/outputs/' directory with descriptive names
6. Print summaries and key statistics for dataframes
7. Use clear variable names and add comments for complex operations
8. When loading data, check if files exist first
9. Display the first few rows of dataframes after loading

AVAILABLE LIBRARIES:
- pandas, numpy (data manipulation)
- matplotlib, seaborn, plotly (visualization)
- scikit-learn (machine learning)
- scipy, statsmodels (statistics)
- requests (API calls)
- All standard Python libraries

OUTPUT FORMAT:
Return only the Python code that can be directly executed.""",

        "code_improvement": """You are a Python code optimization expert.

When improving code:
1. Optimize for readability and performance
2. Follow PEP 8 style guidelines
3. Add type hints where appropriate
4. Improve error handling
5. Add docstrings to functions
6. Suggest more efficient algorithms or libraries
7. Keep the original functionality intact""",

        "error_fixing": """You are a Python debugging expert.

When fixing errors:
1. Analyze the error message and traceback
2. Identify the root cause
3. Provide a corrected version of the code
4. Add error handling to prevent similar issues
5. Explain what went wrong (as a comment in the code)""",

        "visualization": """You are a data visualization expert.

When creating visualizations:
1. Choose appropriate chart types for the data
2. Use clear titles and labels
3. Add legends when necessary
4. Use color effectively
5. Save high-quality figures (dpi=300)
6. Create interactive plots with plotly when appropriate
7. Generate multiple views if it helps understanding"""
    }
    
    def __init__(self,
                 provider: LLMProvider = LLMProvider.OPENAI,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2000):
        """
        Initialize LLM Service
        
        Args:
            provider: LLM provider to use
            api_key: API key for the provider
            model: Model to use
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
        """
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize provider client
        if provider == LLMProvider.OPENAI:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not provided")
            
            # Fixed initialization without proxies
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.model = model or "gpt-4o-mini"  # Changed to gpt-4o-mini
            
            # Only initialize tokenizer if tiktoken is available
            try:
                import tiktoken
                self.tokenizer = tiktoken.encoding_for_model("gpt-4-turbo")  # Use a known model
            except:
                self.tokenizer = None
            
        elif provider == LLMProvider.ANTHROPIC:
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("Anthropic API key not provided")
            
            # Initialize with required headers
            self.client = AsyncAnthropic(
                api_key=self.api_key,
                default_headers={"anthropic-version": "2023-06-01"}
            )
            self.model = model or "claude-3-5-sonnet-20241022"
            
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        # Cache for recent generations
        self.generation_cache = {}
        
        logger.info(f"LLMService initialized with provider: {provider}, model: {self.model}")
    
    async def generate_code(self,
                          query: str,
                          context: Optional[AnalysisContext] = None,
                          task_type: str = "data_analysis") -> CodeGeneration:
        """
        Generate Python code from natural language query
        
        Args:
            query: Natural language query
            context: Analysis context
            task_type: Type of task (data_analysis, code_improvement, etc.)
            
        Returns:
            CodeGeneration object
        """
        # Check cache
        cache_key = f"{query}:{task_type}:{context.session_id if context else 'none'}"
        if cache_key in self.generation_cache:
            logger.info("Returning cached generation")
            return self.generation_cache[cache_key]
        
        # Build prompt
        system_prompt = self.SYSTEM_PROMPTS.get(task_type, self.SYSTEM_PROMPTS["data_analysis"])
        messages = self._build_messages(query, context, system_prompt)
        
        try:
            # Generate code
            if self.provider == LLMProvider.OPENAI:
                code = await self._generate_openai(messages)
            elif self.provider == LLMProvider.ANTHROPIC:
                code = await self._generate_anthropic(messages)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            # Process and validate code
            code = self._process_code(code)
            
            # Extract metadata
            explanation = self._extract_explanation(code)
            libraries = self._extract_libraries(code)
            warnings = self._validate_code(code, context)
            
            generation = CodeGeneration(
                code=code,
                explanation=explanation,
                confidence=0.95 if not warnings else 0.8,
                libraries_used=libraries,
                estimated_runtime="< 5 seconds",
                warnings=warnings
            )
            
            # Cache result
            self.generation_cache[cache_key] = generation
            
            return generation
            
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            # Return a safe fallback
            return CodeGeneration(
                code=f"# Error generating code: {str(e)}\nprint('Failed to generate code. Please try rephrasing your request.')",
                explanation="Code generation failed",
                confidence=0.0,
                libraries_used=[],
                estimated_runtime="N/A",
                warnings=[str(e)]
            )
    
    def _build_messages(self, 
                       query: str,
                       context: Optional[AnalysisContext],
                       system_prompt: str) -> List[Dict[str, str]]:
        """Build messages for LLM"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context if available
        if context:
            context_info = []
            
            # Add available files
            if context.available_files:
                context_info.append(f"Available files in workspace:\n" + 
                                  "\n".join(f"- {f}" for f in context.available_files[:10]))
            
            # Add variables in scope
            if context.variables_in_scope:
                context_info.append("Variables currently in scope:\n" +
                                  "\n".join(f"- {k}: {v}" for k, v in list(context.variables_in_scope.items())[:10]))
            
            # Add recent code execution
            if context.previous_code and len(context.previous_code) > 0:
                recent_code = context.previous_code[-3:]  # Last 3 executions
                context_info.append("Recent code executions:\n" +
                                  "\n---\n".join(recent_code))
            
            if context_info:
                messages.append({
                    "role": "system",
                    "content": "CONTEXT:\n" + "\n\n".join(context_info)
                })
        
        # Add user query
        messages.append({"role": "user", "content": query})
        
        return messages
    
    async def _generate_openai(self, messages: List[Dict[str, str]]) -> str:
        """Generate code using OpenAI"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=0.95,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        return response.choices[0].message.content
    
    async def _generate_anthropic(self, messages: List[Dict[str, str]]) -> str:
        """Generate code using Anthropic"""
        # Convert messages to Anthropic format
        system = messages[0]["content"]
        user_messages = []
        
        for msg in messages[1:]:
            if msg["role"] == "system":
                system += "\n\n" + msg["content"]
            else:
                user_messages.append(msg)
        
        response = await self.client.messages.create(
            model=self.model,
            messages=user_messages,
            system=system,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.content[0].text
    
    def _process_code(self, raw_code: str) -> str:
        """Process and clean generated code"""
        # Remove markdown code blocks if present
        code = re.sub(r'^```python\n', '', raw_code)
        code = re.sub(r'^```\n', '', code)
        code = re.sub(r'\n```$', '', code)
        
        # Remove any explanatory text before the first import or code line
        lines = code.split('\n')
        code_started = False
        clean_lines = []
        
        for line in lines:
            # Check if this looks like code
            if not code_started:
                if (line.strip().startswith('import ') or 
                    line.strip().startswith('from ') or
                    line.strip().startswith('#') or
                    line.strip().startswith('def ') or
                    line.strip().startswith('class ') or
                    '=' in line or
                    line.strip().startswith('print(')):
                    code_started = True
            
            if code_started or line.strip() == '':
                clean_lines.append(line)
        
        return '\n'.join(clean_lines).strip()
    
    def _extract_explanation(self, code: str) -> str:
        """Extract explanation from code comments"""
        lines = code.split('\n')
        explanations = []
        
        for line in lines:
            if line.strip().startswith('#') and not line.strip().startswith('#!'):
                comment = line.strip()[1:].strip()
                if comment and not comment.startswith('---'):
                    explanations.append(comment)
        
        return ' '.join(explanations[:3]) if explanations else "Code generated successfully"
    
    def _extract_libraries(self, code: str) -> List[str]:
        """Extract imported libraries from code"""
        libraries = set()
        
        # Match import statements
        import_pattern = r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)'
        
        for line in code.split('\n'):
            match = re.match(import_pattern, line)
            if match:
                library = match.group(1).split('.')[0]
                libraries.add(library)
        
        return sorted(list(libraries))
    
    def _validate_code(self, code: str, context: Optional[AnalysisContext]) -> List[str]:
        """Validate generated code and return warnings"""
        warnings = []
        
        # Check for potentially dangerous operations
        dangerous_patterns = [
            (r'exec\s*\(', "Code contains exec() which can be dangerous"),
            (r'eval\s*\(', "Code contains eval() which can be dangerous"),
            (r'__import__', "Code contains __import__ which may have security implications"),
            (r'subprocess', "Code uses subprocess which may have security implications"),
            (r'os\.system', "Code uses os.system() which may have security implications"),
        ]
        
        for pattern, warning in dangerous_patterns:
            if re.search(pattern, code):
                warnings.append(warning)
        
        # Check for file operations outside workspace
        if '/workspace/' not in code and any(op in code for op in ['open(', 'with open', 'pd.read_', 'np.load']):
            warnings.append("File operations should use '/workspace/' directory")
        
        # Check for missing imports
        used_functions = {
            'pd.': 'pandas',
            'np.': 'numpy',
            'plt.': 'matplotlib.pyplot',
            'sns.': 'seaborn',
            'plotly.': 'plotly'
        }
        
        for usage, library in used_functions.items():
            if usage in code and f'import {library}' not in code and f'from {library}' not in code:
                warnings.append(f"Code uses {usage} but doesn't import {library}")
        
        return warnings
    
    async def improve_code(self, code: str, improvement_type: str = "optimize") -> CodeGeneration:
        """
        Improve existing code
        
        Args:
            code: Code to improve
            improvement_type: Type of improvement (optimize, style, document)
            
        Returns:
            Improved code
        """
        query = f"""Improve the following code with focus on {improvement_type}:

```python
{code}
```"""
        
        return await self.generate_code(query, task_type="code_improvement")
    
    async def fix_error(self,
                        code: str,
                        error_message: str,
                        traceback: List[str]) -> CodeGeneration:
        """
        Fix code based on error message
        
        Args:
            code: Code that caused the error
            error_message: Error message
            traceback: Error traceback
            
        Returns:
            Fixed code
        """
        query = f"""Fix the following error in the code:

ERROR: {error_message}

TRACEBACK:
{''.join(traceback)}

CODE:
```python
{code}
```"""
        
        return await self.generate_code(query, task_type="error_fixing")
    
    async def generate_visualization(self,
                                    data_description: str,
                                    context: Optional[AnalysisContext] = None) -> CodeGeneration:
        """
        Generate visualization code
        
        Args:
            data_description: Description of data to visualize
            context: Analysis context
            
        Returns:
            Visualization code
        """
        query = f"Create comprehensive visualizations for: {data_description}"
        
        return await self.generate_code(query, context, task_type="visualization")
    
    async def explain_code(self, code: str) -> str:
        """
        Explain what code does
        
        Args:
            code: Code to explain
            
        Returns:
            Explanation
        """
        messages = [
            {
                "role": "system",
                "content": "You are a Python expert. Explain the following code clearly and concisely."
            },
            {
                "role": "user",
                "content": f"Explain this code:\n\n```python\n{code}\n```"
            }
        ]
        
        if self.provider == LLMProvider.OPENAI:
            response = await self._generate_openai(messages)
        else:
            response = await self._generate_anthropic(messages)
        
        return response
    
    async def suggest_next_steps(self,
                                 context: AnalysisContext,
                                 goal: Optional[str] = None) -> List[str]:
        """
        Suggest next analysis steps
        
        Args:
            context: Current analysis context
            goal: Optional analysis goal
            
        Returns:
            List of suggested next steps
        """
        recent_code = "\n---\n".join(context.previous_code[-3:]) if context.previous_code else "No code executed yet"
        
        query = f"""Based on the following analysis context, suggest 5 next steps:

GOAL: {goal or 'General data analysis'}

RECENT CODE:
{recent_code}

AVAILABLE FILES:
{', '.join(context.available_files[:10]) if context.available_files else 'None'}

Provide 5 specific, actionable suggestions for continuing the analysis."""
        
        messages = [
            {"role": "system", "content": "You are a data science expert. Provide specific, actionable suggestions."},
            {"role": "user", "content": query}
        ]
        
        if self.provider == LLMProvider.OPENAI:
            response = await self._generate_openai(messages)
        else:
            response = await self._generate_anthropic(messages)
        
        # Parse suggestions
        suggestions = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean up the suggestion
                suggestion = re.sub(r'^[\d\-•\.]+\s*', '', line)
                if suggestion:
                    suggestions.append(suggestion)
        
        return suggestions[:5]
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if self.provider == LLMProvider.OPENAI and hasattr(self, 'tokenizer'):
            return len(self.tokenizer.encode(text))
        else:
            # Rough estimate: 1 token ≈ 4 characters
            return len(text) // 4
    
    async def check_api_status(self) -> bool:
        """
        Check if the LLM API is available
        
        Returns:
            True if API is available
        """
        try:
            # Simple test query
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with 'OK'"}
            ]
            
            if self.provider == LLMProvider.OPENAI:
                await self._generate_openai(test_messages)
            else:
                await self._generate_anthropic(test_messages)
            
            return True
        except Exception as e:
            logger.error(f"Failed to check API status: {e}")
            return False
    
    async def generate_response(self, message: str) -> str:
        """Generate a simple text response from the LLM"""
        try:
            if self.provider == LLMProvider.ANTHROPIC:
                response = await self.client.messages.create(
                    model=self.model,
                    messages=[{"role": "user", "content": message}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                return response.content[0].text if response.content else ""
            
            elif self.provider == LLMProvider.OPENAI:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": message}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                return response.choices[0].message.content if response.choices else ""
            
            return ""
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return f"Error: {str(e)}"
