import os
import openai
import json

clothing_description_1 = 'What would be really cool is a black sweater'

vinted_input_custom_functions = [
    {
        'name': 'extract_vinted_input',
        'description': 'Get the clothing information from the body of the input text',
        'parameters': {
            'type': 'object',
            'properties': {
                'garment': {
                    'type': 'string',
                    'description': 'Clothing item.'
                    
                },
                'color': {
                    'type': 'string',
                    'enumerate': ['Blue', 'Navy', 'Light Blue', 'Black', 'Gray', 'White', 'Multi', 'Khaki', 'Burgundy', 'Mustard', 'Mint', 'Yellow'],
                    'description': 'Color.'
                }
                
            }
        }
    }
]

response = openai.ChatCompletion.create(
        model = 'gpt-3.5-turbo',
        messages = [{'role': 'user', 'content': clothing_description_1}],
        functions = vinted_input_custom_functions,
        function_call = 'auto'
    )

# Loading the response as a JSON object
response = json.loads(response['choices'][0]['message']['function_call']['arguments'])
print(response)
