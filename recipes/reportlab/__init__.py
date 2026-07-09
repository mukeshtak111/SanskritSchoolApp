from pythonforandroid.recipe import PythonRecipe

class ReportLabRecipe(PythonRecipe):
    version = '4.0.0'
    url = 'https://files.pythonhosted.org/packages/source/r/reportlab/reportlab-{version}.tar.gz'
    depends = ['setuptools']

recipe = ReportLabRecipe()
