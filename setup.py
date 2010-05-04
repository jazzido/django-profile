from distutils.core import setup

setup(name='userprofile',
      version='0.6',
      description='Django pluggable user profile zone',
      author='David Rubert',
      packages=['userprofile',
                'userprofile.templatetags',
                'userprofile.urls'],
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Web Environment',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Utilities'],
      package_data = {
        'userprofile' : [ 'templates/userprofile/*.html', 
                          'templates/userprofile/account/*.html', 
                          'templates/userprofile/account/includes/*.html', 
                          'templates/userprofile/avatar/*.html', 
                          'templates/userprofile/email/*.txt', 
                          'templates/userprofile/profile/*.html', 
                          'locale/*/*/*', ]
        },
)

