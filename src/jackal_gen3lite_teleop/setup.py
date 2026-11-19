import os
from glob import glob

from setuptools import setup

package = 'jackal_gen3lite_teleop'

setup(
    name=package,
    version='0.1.0',
    packages=[package],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package]),
        ('share/' + package, ['package.xml']),
        (os.path.join('share', package, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='haidar',
    maintainer_email='user@example.com',
    description='Keyboard teleop for Jackal + Gen3 lite',
    license='MIT',
    entry_points={
        'console_scripts': [
            'keyboard_teleop = jackal_gen3lite_teleop.keyboard_teleop:main',
        ],
    },
)
