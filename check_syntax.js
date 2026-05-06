const fs = require('fs');
const path = 'company_system/templates/task_management/personal_board_detail.html';
const html = fs.readFileSync(path, 'utf8');
// Find last <script> tag (the inline one)
const start = html.lastIndexOf('<script>');
const end = html.lastIndexOf('</script>');
if (start === -1 || end === -1) {
  console.error('Script tags not found');
  process.exit(1);
}
let js = html.slice(start + 7, end);
// Remove Django template tags - they cause syntax errors
js = js.replace(/{%[\s\S]*?%}/g, '');           // remove {% ... %}
js = js.replace(/\{\{[^}]*\}\}/g, 'null');       // replace {{ ... }} with null
try {
  new Function(js);
  console.log('✓ JavaScript syntax is valid');
} catch (e) {
  console.error('✗ Syntax error:', e.message);
  // Print line number roughly
  const match = e.message.match(/\((\d+):(\d+)\)/);
  if (match) {
    const line = parseInt(match[1]);
    console.error('Error near line', line);
  }
  process.exit(1);
}
