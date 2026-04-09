When making changes to the codebase, please follow these guidelines:
1. Ensure that your code adheres to the existing coding style and conventions used in the project.
2. Avoid adding defensive programming practices, such as adding checks for conditions that should not occur if the code is used correctly. Instead, focus on writing clear and concise code that assumes correct usage since this is an internal data science codespace, not an external software library.
3. Test changes using the --test flag to avoid running the full analysis on large datasets.