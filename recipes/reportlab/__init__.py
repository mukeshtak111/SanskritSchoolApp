from pythonforandroid.recipe import PythonRecipe

class ReportLabRecipe(PythonRecipe):
    version = "4.4.2"
    url = "https://files.pythonhosted.org/packages/source/r/reportlab/reportlab-{version}.tar.gz"
    
    depends = ["python3", "setuptools"]
    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        # यह मास्टरस्ट्रोक C-extensions को हमेशा के लिए ब्लॉक कर देगा
        env['PUREPYTHON'] = '1'
        return env

recipe = ReportLabRecipe()
