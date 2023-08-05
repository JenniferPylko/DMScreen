import sass
open("static/style.css", 'w').write(sass.compile(filename='./src/style.scss', output_style='compressed'))
print("Compiled SCSS")