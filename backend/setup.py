from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension(
        "analysis._coding_orfs_cy",
        ["analysis/_coding_orfs_cy.pyx"],
    ),
    Extension(
        "analysis._promoters_cy",
        ["analysis/_promoters_cy.pyx"],
    ),
    Extension(
        "analysis._shine_dalgarno_cy",
        ["analysis/_shine_dalgarno_cy.pyx"],
    ),
    Extension(
        "analysis._terminators_cy",
        ["analysis/_terminators_cy.pyx"],
    ),
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "nonecheck": False,
            "cdivision": True,
        },
    ),
    zip_safe=False,
)
