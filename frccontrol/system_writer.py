"""A class that handles writing out matrices of a system to a C++ or Java file.
"""

import numpy as np
import os


class SystemWriter:

    def __init__(self, system, system_name, period_variant=False):
        """Exports matrices to pair of C++ source files.

        Keyword arguments:
        system -- System object
        system_name -- subsystem class name in camel case
        period_variant -- True to use PeriodVariantLoop, False to use
                          StateSpaceLoop
        """
        self.system = system
        self.system_name = system_name
        template = "<" + str(system.sysd.A.shape[0]) + ", " + str(
            system.sysd.B.shape[1]) + ", " + str(system.sysd.C.shape[0]) + ">"

        self.period_variant = period_variant
        if period_variant:
            self.class_type = "PeriodVariant"
            self.plant_coeffs_header = "PeriodVariantPlantCoeffs"
            self.obsv_coeffs_header = "PeriodVariantKalmanFilterCoeffs"
            self.loop_header = "PeriodVariantLoop"
        else:
            self.class_type = "StateSpace"
            self.plant_coeffs_header = "StateSpacePlantCoeffs"
            self.obsv_coeffs_header = "StateSpaceObserverCoeffs"
            self.loop_header = "StateSpaceLoop"

        self.ctrl_coeffs_header = "StateSpaceControllerCoeffs"
        self.ctrl_coeffs_type = "frc::" + self.ctrl_coeffs_header + template
        self.plant_coeffs_type = "frc::" + self.plant_coeffs_header + template
        self.obsv_coeffs_type = "frc::" + self.obsv_coeffs_header + template
        self.loop_type = "frc::" + self.loop_header + template

    def write_cpp_header(self):
        """Writes C++ header file."""
        prefix = "#include <frc/controllers/"
        headers = []
        headers.append(prefix + self.plant_coeffs_header + ".h>")
        headers.append(prefix + self.ctrl_coeffs_header + ".h>")
        headers.append(prefix + self.obsv_coeffs_header + ".h>")
        headers.append(prefix + self.loop_header + ".h>")

        with open(self.system_name + "Coeffs.h", "w") as header_file:
            print("#pragma once" + os.linesep, file=header_file)
            for header in sorted(headers):
                print(header, file=header_file)
            header_file.write(os.linesep)
            self.__write_cpp_func_name(
                header_file,
                self.plant_coeffs_type,
                "PlantCoeffs",
                in_header=True)
            self.__write_cpp_func_name(
                header_file,
                self.ctrl_coeffs_type,
                "ControllerCoeffs",
                in_header=True)
            self.__write_cpp_func_name(
                header_file,
                self.obsv_coeffs_type,
                "ObserverCoeffs",
                in_header=True)
            self.__write_cpp_func_name(
                header_file, self.loop_type, "Loop", in_header=True)

    def write_cpp_source(self, header_path_prefix):
        """Writes C++ source file.

        Keyword arguments:
        header_path_prefix -- path prefix in which header exists
        """
        if len(header_path_prefix) > 0 and header_path_prefix[-1] != os.sep:
            header_path_prefix += os.sep

        with open(self.system_name + "Coeffs.cpp", "w") as source_file:
            print(
                "#include \"" + header_path_prefix + self.system_name +
                "Coeffs.h\"" + os.linesep,
                file=source_file)
            print("#include <Eigen/Core>" + os.linesep, file=source_file)

            # Write MakePlantCoeffs()
            self.__write_cpp_func_name(
                source_file,
                self.plant_coeffs_type,
                "PlantCoeffs",
                in_header=False)
            if self.period_variant:
                self.__write_cpp_matrix(source_file, self.system.sysc.A,
                                        "Acontinuous")
                self.__write_cpp_matrix(source_file, self.system.sysc.B,
                                        "Bcontinuous")
                self.__write_cpp_matrix(source_file, self.system.sysd.C, "C")
                self.__write_cpp_matrix(source_file, self.system.sysd.D, "D")
                print(
                    "  return " + self.plant_coeffs_type +
                    "(Acontinuous, Bcontinuous, C, D);",
                    file=source_file)
            else:
                self.__write_cpp_matrix(source_file, self.system.sysd.A, "A")
                self.__write_cpp_matrix(source_file,
                                        np.linalg.inv(self.system.sysd.A),
                                        "Ainv")
                self.__write_cpp_matrix(source_file, self.system.sysd.B, "B")
                self.__write_cpp_matrix(source_file, self.system.sysd.C, "C")
                self.__write_cpp_matrix(source_file, self.system.sysd.D, "D")
                print(
                    "  return " + self.plant_coeffs_type +
                    "(A, Ainv, B, C, D);",
                    file=source_file)
            print("}" + os.linesep, file=source_file)

            # Write MakeControllerCoeffs()
            self.__write_cpp_func_name(
                source_file,
                self.ctrl_coeffs_type,
                "ControllerCoeffs",
                in_header=False)
            self.__write_cpp_matrix(source_file, self.system.K, "K")
            self.__write_cpp_matrix(source_file, self.system.Kff, "Kff")
            self.__write_cpp_matrix(source_file, self.system.u_min, "Umin")
            self.__write_cpp_matrix(source_file, self.system.u_max, "Umax")
            print(
                "  return " + self.ctrl_coeffs_type + "(K, Kff, Umin, Umax);",
                file=source_file)
            print("}" + os.linesep, file=source_file)

            # Write MakeObserverCoeffs()
            self.__write_cpp_func_name(
                source_file,
                self.obsv_coeffs_type,
                "ObserverCoeffs",
                in_header=False)
            if self.period_variant:
                self.__write_cpp_matrix(source_file, self.system.Q,
                                        "Qcontinuous")
                self.__write_cpp_matrix(source_file, self.system.R,
                                        "Rcontinuous")
                self.__write_cpp_matrix(source_file, self.system.P_steady,
                                        "PsteadyState")

                first_line_prefix = "  return " + self.obsv_coeffs_type + "("
                space_prefix = " " * len(first_line_prefix)
                print(
                    first_line_prefix + "Qcontinuous, Rcontinuous,",
                    file=source_file)
                print(space_prefix + "PsteadyState);", file=source_file)
            else:
                self.__write_cpp_matrix(source_file, self.system.L, "L")
                print(
                    "  return " + self.obsv_coeffs_type + "(L);",
                    file=source_file)
            print("}" + os.linesep, file=source_file)

            # Write MakeLoop()
            self.__write_cpp_func_name(
                source_file, self.loop_type, "Loop", in_header=False)
            first_line_prefix = "  return " + self.loop_type + "("
            space_prefix = " " * len(first_line_prefix)
            print(
                first_line_prefix + "Make" + self.system_name +
                "PlantCoeffs(),",
                file=source_file)
            print(
                space_prefix + "Make" + self.system_name +
                "ControllerCoeffs(),",
                file=source_file)
            print(
                space_prefix + "Make" + self.system_name + "ObserverCoeffs());",
                file=source_file)
            print("}", file=source_file)

    def __write_cpp_func_name(self, cpp_file, return_type, object_suffix,
                              in_header):
        """Writes either declaration or definition of C++ factory function.

        Keyword arguments:
        cpp_file -- file object to which to write name
        return_type -- string containing the return type
        object_suffix -- asdf
        in_header -- if True, print prototype instead of declaration
        """
        if in_header:
            func_suffix = ";"
        else:
            func_suffix = " {"
        func_name = "Make" + self.system_name + object_suffix + "()" + func_suffix
        if len(return_type + " " + func_name) > 80:
            print(return_type, file=cpp_file)
            print(func_name, file=cpp_file)
        else:
            print(return_type + " " + func_name, file=cpp_file)

    def __write_cpp_matrix(self, cpp_file, matrix, matrix_name):
        print(
            "  Eigen::Matrix<double, " + str(matrix.shape[0]) + ", " + str(
                matrix.shape[1]) + "> " + matrix_name + ";",
            file=cpp_file)
        for row in range(matrix.shape[0]):
            for col in range(matrix.shape[1]):
                print(
                    "  " + matrix_name + "(" + str(row) + ", " + str(col) +
                    ") = " + str(matrix[row, col]) + ";",
                    file=cpp_file)
