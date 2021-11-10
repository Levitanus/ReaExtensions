# import lilypond as ly
from rea_extensions.ly_lib import musicexp as exp
import io

output = io.StringIO()

printer = exp.Output_printer()

printer.set_file(output)

print(output)
