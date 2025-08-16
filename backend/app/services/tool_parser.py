"""
Tool-calling DSL parser for comment directives
Parses @tool comments in code and converts to API calls
"""

import re
import ast
import json
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class ToolParser:
    """Parses tool directives from code comments"""
    
    def __init__(self):
        self.tool_pattern = re.compile(r'#\s*@tool:(\w+)\((.*?)\)')
        self.supported_tools = {
            'save_csv': self._parse_save_csv,
            'plot': self._parse_plot,
            'save_json': self._parse_save_json,
            'load_data': self._parse_load_data,
            'export_model': self._parse_export_model,
            'create_report': self._parse_create_report
        }
    
    def parse_code(self, code: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Parse code and extract tool directives"""
        lines = code.split('\n')
        cleaned_lines = []
        tool_calls = []
        
        for line in lines:
            match = self.tool_pattern.search(line)
            if match:
                tool_name = match.group(1)
                tool_args = match.group(2)
                
                if tool_name in self.supported_tools:
                    try:
                        parsed_call = self.supported_tools[tool_name](tool_args)
                        tool_calls.append({
                            'tool': tool_name,
                            'args': parsed_call,
                            'original_line': line.strip()
                        })
                        # Replace with actual Python code
                        cleaned_lines.append(self._generate_python_code(tool_name, parsed_call))
                    except Exception as e:
                        logger.warning(f"Failed to parse tool directive {line}: {e}")
                        cleaned_lines.append(line)  # Keep original line
                else:
                    logger.warning(f"Unknown tool: {tool_name}")
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines), tool_calls
    
    def _parse_save_csv(self, args_str: str) -> Dict[str, Any]:
        """Parse save_csv tool arguments"""
        # Expected: "filename.csv", dataframe_variable
        args = self._parse_function_args(args_str)
        return {
            'filename': args[0],
            'dataframe': args[1] if len(args) > 1 else 'df'
        }
    
    def _parse_plot(self, args_str: str) -> Dict[str, Any]:
        """Parse plot tool arguments"""
        # Expected: "plot_type", x="column", y="column", **kwargs
        args, kwargs = self._parse_function_args_kwargs(args_str)
        return {
            'plot_type': args[0] if args else 'line',
            'params': kwargs
        }
    
    def _parse_save_json(self, args_str: str) -> Dict[str, Any]:
        """Parse save_json tool arguments"""
        args = self._parse_function_args(args_str)
        return {
            'filename': args[0],
            'data': args[1] if len(args) > 1 else 'data'
        }
    
    def _parse_load_data(self, args_str: str) -> Dict[str, Any]:
        """Parse load_data tool arguments"""
        args = self._parse_function_args(args_str)
        return {
            'filename': args[0],
            'format': args[1] if len(args) > 1 else 'auto'
        }
    
    def _parse_export_model(self, args_str: str) -> Dict[str, Any]:
        """Parse export_model tool arguments"""
        args = self._parse_function_args(args_str)
        return {
            'model_name': args[0],
            'model_object': args[1] if len(args) > 1 else 'model'
        }
    
    def _parse_create_report(self, args_str: str) -> Dict[str, Any]:
        """Parse create_report tool arguments"""
        args, kwargs = self._parse_function_args_kwargs(args_str)
        return {
            'title': args[0] if args else 'Analysis Report',
            'sections': kwargs.get('sections', ['summary', 'plots', 'data'])
        }
    
    def _parse_function_args(self, args_str: str) -> List[str]:
        """Parse function arguments from string"""
        try:
            # Use AST to safely parse arguments
            parsed = ast.parse(f"f({args_str})")
            call_node = parsed.body[0].value
            
            args = []
            for arg in call_node.args:
                if isinstance(arg, ast.Constant):
                    args.append(arg.value)
                elif isinstance(arg, ast.Name):
                    args.append(arg.id)
                else:
                    args.append(ast.unparse(arg))
            
            return args
        except Exception as e:
            logger.warning(f"Failed to parse args {args_str}: {e}")
            return []
    
    def _parse_function_args_kwargs(self, args_str: str) -> Tuple[List[str], Dict[str, Any]]:
        """Parse function arguments and keyword arguments"""
        try:
            parsed = ast.parse(f"f({args_str})")
            call_node = parsed.body[0].value
            
            args = []
            kwargs = {}
            
            for arg in call_node.args:
                if isinstance(arg, ast.Constant):
                    args.append(arg.value)
                elif isinstance(arg, ast.Name):
                    args.append(arg.id)
                else:
                    args.append(ast.unparse(arg))
            
            for keyword in call_node.keywords:
                if isinstance(keyword.value, ast.Constant):
                    kwargs[keyword.arg] = keyword.value.value
                elif isinstance(keyword.value, ast.Name):
                    kwargs[keyword.arg] = keyword.value.id
                else:
                    kwargs[keyword.arg] = ast.unparse(keyword.value)
            
            return args, kwargs
        except Exception as e:
            logger.warning(f"Failed to parse args/kwargs {args_str}: {e}")
            return [], {}
    
    def _generate_python_code(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Generate actual Python code for tool directive"""
        if tool_name == 'save_csv':
            return f"{args['dataframe']}.to_csv('{args['filename']}', index=False)"
        
        elif tool_name == 'plot':
            plot_type = args['plot_type']
            params = args['params']
            
            if plot_type == 'scatter':
                x = params.get('x', 'x')
                y = params.get('y', 'y')
                return f"plt.scatter(df['{x}'], df['{y}'])\nplt.xlabel('{x}')\nplt.ylabel('{y}')\nplt.title('Scatter Plot')\nplt.show()"
            
            elif plot_type == 'line':
                x = params.get('x', 'x')
                y = params.get('y', 'y')
                return f"plt.plot(df['{x}'], df['{y}'])\nplt.xlabel('{x}')\nplt.ylabel('{y}')\nplt.title('Line Plot')\nplt.show()"
            
            elif plot_type == 'histogram':
                column = params.get('column', 'value')
                return f"plt.hist(df['{column}'], bins=30)\nplt.xlabel('{column}')\nplt.ylabel('Frequency')\nplt.title('Histogram')\nplt.show()"
            
            elif plot_type == 'bar':
                x = params.get('x', 'category')
                y = params.get('y', 'value')
                return f"plt.bar(df['{x}'], df['{y}'])\nplt.xlabel('{x}')\nplt.ylabel('{y}')\nplt.title('Bar Chart')\nplt.xticks(rotation=45)\nplt.show()"
        
        elif tool_name == 'save_json':
            return f"import json\nwith open('{args['filename']}', 'w') as f:\n    json.dump({args['data']}, f, indent=2)"
        
        elif tool_name == 'load_data':
            filename = args['filename']
            format_type = args['format']
            
            if format_type == 'auto':
                if filename.endswith('.csv'):
                    return f"df = pd.read_csv('{filename}')"
                elif filename.endswith('.json'):
                    return f"import json\nwith open('{filename}', 'r') as f:\n    data = json.load(f)"
                elif filename.endswith('.xlsx'):
                    return f"df = pd.read_excel('{filename}')"
            else:
                if format_type == 'csv':
                    return f"df = pd.read_csv('{filename}')"
                elif format_type == 'json':
                    return f"import json\nwith open('{filename}', 'r') as f:\n    data = json.load(f)"
        
        elif tool_name == 'export_model':
            return f"import joblib\njoblib.dump({args['model_object']}, '{args['model_name']}.pkl')"
        
        elif tool_name == 'create_report':
            return f"# Creating report: {args['title']}\nprint('Report generated with sections: {args['sections']}')"
        
        return f"# Tool {tool_name} not implemented"

# Global parser instance
tool_parser = ToolParser()
