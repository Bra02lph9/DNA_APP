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
    name="dna_analysis_extensions",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
    zip_safe=False,
)
