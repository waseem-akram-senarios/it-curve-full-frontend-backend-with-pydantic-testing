#!/usr/bin/env python3
"""
Simple script to add the missing @function_tool() decorator to book_trips function
"""

import re

def fix_book_trips_decorator():
    """Add the missing @function_tool() decorator to book_trips function"""
    
    file_path = "/home/senarios/VoiceAgent5withFeNew/VoiceAgent3/IT_Curves_Bot/helper_functions.py"
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the book_trips function definition and add the decorator
    # Look for "async def book_trips(self) -> str:" without the decorator
    pattern = r'(?<!@function_tool\(\)\s*\n\s*)(async def book_trips\(self\) -> str:)'
    
    if re.search(pattern, content):
        # Add the decorator
        new_content = re.sub(pattern, r'@function_tool()\n    \1', content)
        
        # Write the updated content
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Successfully added @function_tool() decorator to book_trips function")
        return True
    else:
        print("❌ Could not find book_trips function or decorator already exists")
        return False

if __name__ == "__main__":
    fix_book_trips_decorator()

