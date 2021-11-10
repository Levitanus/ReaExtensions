# import lilypond as ly
import reapy as rpr

from fractions import Fraction
from rea_extensions import lilypond as ly
from rea_extensions.ly_lib import musicexp as exp

from fractions import Fraction
from pprint import pprint

item = rpr.Project().selected_items[0]
out = ly.item_to_ly(item)

print('\\version "2.19"', out, sep='\n')
