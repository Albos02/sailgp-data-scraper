#!/usr/bin/env python3
"""
Simple JSON formatter script
Reads a JSON file and outputs it with proper formatting
"""

import json
import sys


def format_json(input_file, output_file=None, indent=2):
    """
    Format a JSON file with proper indentation
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output file (optional, overwrites input if not provided)
        indent: Number of spaces for indentation (default: 2)
    """
    try:
        # Read the JSON file
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Format the JSON
        formatted_json = json.dumps(data, indent=indent, sort_keys=True)
        
        # Write to output file or overwrite input
        output_path = output_file if output_file else input_file
        with open(output_path, 'w') as f:
            f.write(formatted_json)
        
        print(f"✓ Successfully formatted JSON and saved to: {output_path}")
        
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in {input_file}")
        print(f"  {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"✗ Error: File not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python format_json.py <input_file> [output_file] [indent]")
        print("\nExamples:")
        print("  python format_json.py data.json              # Format in place")
        print("  python format_json.py data.json output.json  # Save to new file")
        print("  python format_json.py data.json output.json 4  # Use 4-space indent")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    indent = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    
    format_json(input_file, output_file, indent)