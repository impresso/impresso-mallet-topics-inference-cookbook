import dotenv
import os, jpype
import jpype.imports
import sys

dotenv.load_dotenv()
cdir = os.getcwd()
classpath = [
    os.path.join(cdir, j)
    for j in ["mallet/lib/mallet.jar", "mallet/lib/mallet-deps.jar"]
]
print(classpath, file=sys.stderr)
jpype.startJVM(classpath=classpath)
from cc.mallet.classify.tui import Csv2Vectors

sys.exit(0)
