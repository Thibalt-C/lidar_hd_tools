import shutil
import os

# Copier ReadMe.md dans docs/
source_readme = os.path.abspath("../ReadMe.md")
dest_readme = os.path.abspath("ReadMe.md")

if os.path.exists(source_readme):
    shutil.copyfile(source_readme, dest_readme)
