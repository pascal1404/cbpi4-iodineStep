from setuptools import setup

setup(name='cbpi4-iodineStep',
      version='0.0.1',
      description='CraftBeerPi Plugin reminding to do an iodine check',
      author='Pascal Scholz',
      author_email='pascal1404@gmx.de',
      url='https://github.com/pascal1404/cbpi4-iodineStep',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4_cbpi4-iodineStep': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4-iodineStep'],
     )