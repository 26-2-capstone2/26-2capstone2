# Weather coefficient provenance

P.676-12 oxygen/water spectral tables were obtained from the MIT-licensed ITU-Rpy project:
https://github.com/inigodelportillo/ITU-Rpy/tree/master/itur/data/676

Files: v12_lines_oxygen.txt (44 lines), v12_lines_water_vapour.txt (35 lines), renamed to CSV. They are bundled locally; no network is needed at runtime. Original copyright/license: LICENSE_ITU_Rpy.txt.

ituGasSpecific.m implements the ITU Annex 1 summation with reference to ITU-Rpy itu676.py. Rain coefficients are from ITU-R P.838-3 Tables 1-4; cloud equations are from ITU-R P.840-8. See WEATHER_MODEL.md for the distinction between standard absorption equations and assumed weather profiles.
