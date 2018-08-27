# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from setuptools import setup, find_packages
import codecs  # To use a consistent encoding

# Get the long description from the relevant file
with codecs.open('DESCRIPTION.rst', encoding='utf-8') as f:
    long_description = f.read()

with open("requirements.txt") as requirements:
    install_requires = requirements.readlines()

setup(
    name='active_mail_filter',
    version='0.1.0',
    description='Active Mail Filtering',
    long_description=long_description,
    author='Kevin Rodgers',
    author_email='kevin@rodgersworld.com',
    url='https://github.com/kfrodgers/active_mail_filter',
    license='Apache 2.0',
    classifiers=['Development Status :: 4 - Beta',
                 'Intended Audience :: System Administrators',
                 'Intended Audience :: Developers',
                 'Topic :: Software Development :: Libraries :: Python Modules',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python :: 2.7'],
    keywords='filter, mail, imap',
    packages=find_packages(exclude=['test/*.py', 'test_*']),
    scripts=[],
    entry_points={
        'console_scripts': ['amf_add_rule = active_mail_filter.commands:add_rule',
                            'amf_daemon = active_mail_filter.daemon:run_daemon',
                            'amf_del_rule = active_mail_filter.commands:delete_rule',
                            'amf_list_rules = active_mail_filter.commands:list_rules',
                            'amf_mod_rule = active_mail_filter.commands:modify_rule',
                            'amf_start_daemon = active_mail_filter.commands:start_daemon',
                            'amf_stop_daemon = active_mail_filter.commands:stop_daemon',
                            'amf_update_conf = active_mail_filter.commands:update_config']
    },
    install_requires=install_requires,
    data_files=[('/usr/local/etc/', ['conf/amf.conf'])]
)
