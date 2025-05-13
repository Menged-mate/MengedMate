const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Print current directory
console.log('Current directory:', process.cwd());

// Check if frontend directory exists
const frontendDir = path.join(process.cwd(), 'frontend');
if (!fs.existsSync(frontendDir)) {
  console.error('Frontend directory not found!');
  console.log('Contents of current directory:');
  console.log(fs.readdirSync(process.cwd()));
  process.exit(1);
}

// Navigate to frontend directory and run build
try {
  console.log('Changing to frontend directory...');
  process.chdir(frontendDir);
  
  console.log('Installing dependencies...');
  execSync('npm install --legacy-peer-deps', { stdio: 'inherit' });
  
  console.log('Building frontend...');
  execSync('npm run build', { stdio: 'inherit' });
  
  console.log('Build completed successfully!');
} catch (error) {
  console.error('Build failed:', error.message);
  process.exit(1);
}
