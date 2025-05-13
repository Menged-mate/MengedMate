import os
import shutil
from pathlib import Path

def ensure_directory_exists(directory):
    """Ensure that a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
    print(f"Ensured directory exists: {directory}")

def copy_template_file(source, destination):
    """Copy a template file, creating the destination directory if necessary."""
    # Ensure the destination directory exists
    destination_dir = os.path.dirname(destination)
    ensure_directory_exists(destination_dir)
    
    # Copy the file
    try:
        shutil.copy2(source, destination)
        print(f"Successfully copied {source} to {destination}")
        return True
    except Exception as e:
        print(f"Error copying {source} to {destination}: {str(e)}")
        return False

def main():
    """Main function to copy template files."""
    # Get the base directory
    base_dir = Path(__file__).resolve().parent
    
    # Define source and destination paths
    template_source = os.path.join(base_dir, 'templates', 'index.html')
    template_dest = os.path.join(base_dir, 'templates', 'index.html')
    
    # Ensure the templates directory exists
    ensure_directory_exists(os.path.join(base_dir, 'templates'))
    
    # Check if the source file exists
    if not os.path.exists(template_source):
        # Create a simple index.html if it doesn't exist
        print(f"Source file {template_source} does not exist. Creating a simple index.html...")
        with open(template_dest, 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mengedmate - EV Charging Station Locator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background: linear-gradient(135deg, #4a6cf7 0%, #2a3f9d 100%);
            color: white;
            text-align: center;
        }
        .container {
            max-width: 800px;
            padding: 20px;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 20px;
        }
        p {
            font-size: 1.2rem;
            margin-bottom: 30px;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background-color: white;
            color: #4a6cf7;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            margin: 10px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background-color: transparent;
            color: white;
            border: 2px solid white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Mengedmate</h1>
        <p>Find EV Charging Stations Anywhere, Anytime</p>
        <div>
            <a href="/login" class="btn">Login</a>
            <a href="/register" class="btn">Register</a>
        </div>
    </div>
</body>
</html>""")
        print(f"Created simple index.html at {template_dest}")
    else:
        # Copy the template file
        copy_template_file(template_source, template_dest)

if __name__ == "__main__":
    main()
