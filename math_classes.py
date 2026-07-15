"""
Vector3 and Quaternions in Python.
"""

import math


# NOTE: try removing the elifs from the vector calculations if the server is slow.
# it may speed things up and we can rely on Python native errors anyway

class Vector3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x = 0.0, y = 0.0, z = 0.0):
        """Create a Vector3 object."""
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __add__(self, other: Vector3 | int | float):
        if isinstance(other, Vector3):
            return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
        elif not isinstance(other, (int, float)):
            raise TypeError("`other` must be of type Vector3, int, or float.")
        # if other is an int or float
        return Vector3(self.x + other, self.y + other, self.z + other)

    def __sub__(self, other: Vector3 | int | float):
        if isinstance(other, Vector3):
            return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
        elif not isinstance(other, (int, float)):
            raise TypeError("`other` must be of type Vector3, int, or float.")
        # if other is an int or float
        return Vector3(self.x - other, self.y - other, self.z - other)

    def __mul__(self, other: Vector3 | int | float):
        if isinstance(other, Vector3):
            return Vector3(self.x * other.x, self.y * other.y, self.z * other.z)
        elif not isinstance(other, (int, float)):
            raise TypeError("`other` must be of type Vector3, int, or float.")
        # if other is an int or float
        return Vector3(self.x * other, self.y * other, self.z * other)

    def __truediv__(self, other: Vector3 | int | float):
        if isinstance(other, Vector3):
            return Vector3(self.x / other.x, self.y / other.y, self.z / other.z)
        elif not isinstance(other, (int, float)):
            raise TypeError("`other` must be of type Vector3, int, or float.")
        # if other is an int or float
        return Vector3(self.x / other, self.y / other, self.z / other)

    def dot(self, other: Vector3):
        if not isinstance(other, Vector3):
            raise TypeError("`other` must be of type Vector3")

        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3):
        if not isinstance(other, Vector3):
            raise TypeError("`other` must be of type Vector3")

        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self):
        """Returns the length of the vector."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        """Normalizes the vector to a length of 1. Also called a unit vector."""
        return self / abs(self.length())

    def dump(self):
        """Dumps the x, y, and z values, in that order, as a tuple."""
        return self.x, self.y, self.z


class Quaternion:
    __slots__ = ("w", "x", "y", "z")

    def __init__(self, w=1.0, x=0.0, y=0.0, z=0.0):
        """Create a Quaternion object."""
        self.w = float(w)
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __mul__(self, other: Quaternion):
        # Quaternion * Quaternion multiplication
        return Quaternion(
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
        )

    def rotate_vector(self, v: Vector3) -> Vector3:
        """Rotate a vector. I'm honestly not really sure how this works."""
        # Extremely optimized formula: v' = v + 2 * r x (s * v + r x v)
        # Avoids full quaternion-to-matrix conversion overhead.
        tx = 2.0 * (self.y * v.z - self.z * v.y)
        ty = 2.0 * (self.z * v.x - self.x * v.z)
        tz = 2.0 * (self.x * v.y - self.y * v.x)

        cx = self.y * tz - self.z * ty
        cy = self.z * tx - self.x * tz
        cz = self.x * ty - self.y * tx

        return Vector3(
            v.x + self.w * tx + cx, v.y + self.w * ty + cy, v.z + self.w * tz + cz
        )

    def dump(self):
        """Dumps the w, x, y, and z values, in that order, as a tuple."""
        return self.w, self.x, self.y, self.z
