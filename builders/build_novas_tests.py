"""Rebuild the test data that compares Skyfield to the NOVAS library."""

from __future__ import print_function
from itertools import product
from sys import exit
from textwrap import dedent

try:
    from novas import compat as novas
    import novas_de405
except ImportError:
    print(dedent("""\
        Error: to rebuild NOVAS test data, you must install both the "novas"
        package and its default ephemeris:

        pip install novas novas_de405

        """))
    exit(2)

from novas.compat import eph_manager
from novas.constants import ASEC2RAD, T0
nutation_function = novas.nutation
import novas.compat.nutation as nutation_module

planets = [('mercury', 1), ('venus', 2), ('mars', 4), ('jupiter', 5),
           ('saturn', 6), ('uranus', 7), ('neptune', 8), ('pluto', 9),
           ('sun', 10), ('moon', 11)]

def main():
    jd_start, jd_end, number = eph_manager.ephem_open()
    output({}, """\

        import pytest
        from numpy import abs, array, einsum, max
        from skyfield import earthlib, framelib, nutationlib, precessionlib, timelib
        from skyfield.api import JulianDate, earth, mars
        from skyfield.constants import AU_M
        from skyfield.functions import length_of
        from skyfield.jpllib import Ephemeris


        try:
            import de405
            de405 = Ephemeris(de405)
        except ImportError:
            pytestmark = pytest.mark.skipif(True, reason='de405 unavailable')

        one_second = 1.0 / 24.0 / 60.0 / 60.0
        arcsecond = 1.0 / 60.0 / 60.0
        ra_arcsecond = 24.0 / 360.0 / 60.0 / 60.0
        meter = 1.0 / AU_M

        def compare(value, expected_value, epsilon):
            if hasattr(value, 'shape') or hasattr(expected_value, 'shape'):
                assert max(abs(value - expected_value)) <= epsilon
            else:
                assert abs(value - expected_value) <= epsilon

        """)

    moon_landing = novas.julian_date(1969, 7, 20, 20.0 + 18.0/60.0)
    first_hubble_image = novas.julian_date(1990, 5, 20)
    voyager_intersellar = novas.julian_date(2012, 8, 25)

    date_vector = [moon_landing, first_hubble_image, T0, voyager_intersellar]
    dates = date_vector + [date_vector]

    output_subroutine_tests(dates)
    output_geocentric_tests(dates)
    output_topocentric_tests(dates)


def output_subroutine_tests(dates):
    date_floats = [d for d in dates if not isinstance(d, list)]

    def shorter_cal_date(jd):
        y, m, d, h = novas.cal_date(jd)
        return y, m, d + h / 24.0 - 0.5

    for i, jd in enumerate(date_floats):
        cal_date = call(shorter_cal_date, jd)
        output(locals(), """\
            def test_calendar_date_{i}():
                compare(timelib.calendar_date({jd!r}), array({cal_date}), 0.0)
            """)

    for i, jd in enumerate(date_floats):
        angle = novas.era(jd)
        output(locals(), """\
            def test_earth_rotation_angle_date{i}():
                compare(earthlib.earth_rotation_angle({jd!r}), {angle},
                        0.000001 * arcsecond)
            """)

    for i, jd in enumerate(date_floats):
        angles = novas.e_tilt(jd)
        output(locals(), """\
            def test_earth_tilt_date{i}():
                compare(nutationlib.earth_tilt(JulianDate(tdb={jd!r})),
                        array({angles}), 0.00001 * arcsecond)
            """)

    for i, jd in enumerate(date_floats):
        terms = novas.ee_ct(jd, 0.0, 0)
        output(locals(), """\
            def test_equation_of_the_equinoxes_complimentary_terms_date{i}():
                compare(nutationlib.equation_of_the_equinoxes_complimentary_terms({jd!r}),
                        array({terms}), 0.0000000000000001 * arcsecond)
            """)

    vector = (1.1, 1.2, 1.3)
    tie1 = novas.frame_tie(vector, 0)
    tie2 = novas.frame_tie(vector, -1)
    output(locals(), """\
        def test_forward_frame_tie():
            compare(framelib.ICRS_to_J2000.dot({vector}), {tie1}, 1e-15)

        def test_reverse_frame_tie():
            compare(framelib.ICRS_to_J2000.T.dot({vector}), {tie2}, 1e-15)
        """)

    for i, jd in enumerate(date_floats):
        jcentury = (jd - T0) / 36525.0
        arguments = novas.fund_args(jcentury)
        output(locals(), """\
            def test_fundamental_arguments_date{i}():
                compare(nutationlib.fundamental_arguments({jcentury!r}),
                        array({arguments}), 0.000000001 * arcsecond)
            """)

    for i, jd in enumerate(date_floats):
        psi, eps = nutation_module.iau2000a(jd, 0.0)
        psi *= 1e7 / ASEC2RAD
        eps *= 1e7 / ASEC2RAD
        output(locals(), """\
            def test_iau2000a_date{i}():
                compare(nutationlib.iau2000a({jd!r}),
                        array([{psi}, {eps}]), 0.001)
            """)

    for i, args in enumerate([
          (-4712, 1, 1, 0.0),
          (-4712, 3, 1, 0.0),
          (-4712, 12, 31, 0.5),
          (-241, 3, 25, 19.0),
          (530, 9, 27, 23.5),
          (1976, 3, 7, 12.5),
          (2000, 1, 1, 0.0),
          ]):
        jd = novas.julian_date(*args)
        output(locals(), """\
            def test_julian_date_function_date{i}():
                compare(timelib.julian_date{args}, {jd!r}, 0.0)
            """)

    for i, jd in enumerate(date_floats):
        angle = novas.mean_obliq(jd)
        output(locals(), """\
            def test_mean_obliquity_date{i}():
                compare(nutationlib.mean_obliquity({jd!r}),
                        {angle!r}, 0.0)  # arcseconds
            """)

    for i, jd in enumerate(date_floats):
        vector = [1.1, 1.2, 1.3]
        result = nutation_function(jd, vector)
        output(locals(), """\
            def test_nutation_date{i}():
                matrix = nutationlib.compute_nutation(JulianDate(tdb={jd!r}))
                result = einsum('ij...,j...->i...', matrix, [1.1, 1.2, 1.3])
                compare({result},
                        result, 1e-14)
            """)

    for i, jd in enumerate(date_floats):
        vector = [1.1, 1.2, 1.3]
        result = novas.precession(T0, vector, jd)
        output(locals(), """\
            def test_precession_date{i}():
                matrix = precessionlib.compute_precession({jd!r})
                result = einsum('ij...,j...->i...', matrix, [1.1, 1.2, 1.3])
                compare({result},
                        result, 1e-15)
            """)


def output_geocentric_tests(dates):
    for (planet, code), (i, jd) in product(planets, enumerate(dates)):
        obj = novas.make_object(0, code, 'planet{}'.format(code), None)

        ra1, dec1, distance1 = call(novas.astro_planet, jd, obj)
        ra2, dec2, distance2 = call(novas.virtual_planet, jd, obj)
        ra3, dec3, distance3 = call(novas.app_planet, jd, obj)

        assert distance1 == distance2 == distance3

        output(locals(), """\

        def test_{planet}_geocentric_date{i}():
            jd = JulianDate(tt={jd!r})
            e = de405.earth(jd)

            distance = length_of((e - de405.{planet}(jd)).position.AU)
            compare(distance, {distance1!r}, 0.5 * meter)

            astrometric = e.observe(de405.{planet})
            ra, dec, distance = astrometric.radec()
            compare(ra.hours, {ra1!r}, 0.001 * ra_arcsecond)
            compare(dec.degrees, {dec1!r}, 0.001 * arcsecond)

            apparent = astrometric.apparent()
            ra, dec, distance = apparent.radec()
            compare(ra.hours, {ra2!r}, 0.001 * ra_arcsecond)
            compare(dec.degrees, {dec2!r}, 0.001 * arcsecond)

            ra, dec, distance = apparent.radec(epoch='date')
            compare(ra.hours, {ra3!r}, 0.001 * ra_arcsecond)
            compare(dec.degrees, {dec3!r}, 0.001 * arcsecond)

        """)


def output_topocentric_tests(dates):
    usno = novas.make_on_surface(38.9215, -77.0669, 92.0, 10.0, 1010.0)
    for (planet, code), (i, jd) in product(planets, enumerate(dates)):
        obj = novas.make_object(0, code, 'planet{}'.format(code), None)

        ra1, dec1, distance1 = call(novas.local_planet, jd, 0.0, obj, usno)
        ra2, dec2, distance2 = call(novas.topo_planet, jd, 0.0, obj, usno)
        alt, az = call(altaz_maneuver, jd, obj, usno)

        output(locals(), """\

        def test_{planet}_topocentric_date{i}():
            jd = JulianDate(tt={jd!r})
            usno = de405.earth.topos('38.9215 N', '77.0669 W', elevation_m=92.0)

            apparent = usno(jd).observe(de405.{planet}).apparent()
            ra, dec, distance = apparent.radec()
            compare(ra.hours, {ra1!r}, 0.001 * ra_arcsecond)
            compare(dec.degrees, {dec1!r}, 0.001 * arcsecond)

            ra, dec, distance = apparent.radec(epoch='date')
            compare(ra.hours, {ra2!r}, 0.001 * ra_arcsecond)
            compare(dec.degrees, {dec2!r}, 0.001 * arcsecond)

            alt, az, distance = apparent.altaz()
            compare(alt.degrees, {alt!r}, 0.001 * arcsecond)
            compare(az.degrees, {az!r}, 0.001 * arcsecond)

        """)


def altaz_maneuver(jd, obj, place):
    """Simplify a pair of complicated USNO calls to a single callable."""
    xp = yp = 0.0
    ra, dec, distance = novas.topo_planet(jd, 0.0, obj, place)
    (zd, az), (ra, dec) = novas.equ2hor(jd, 0.0, xp, yp, place, ra, dec)
    return 90.0 - zd, az


def call(function, jd, *args):
    """Call function either once, or as many times as `jd` dictates."""

    if isinstance(jd, float):
        return function(jd, *args)

    answers = [function(n, *args) for n in jd]
    return zip(*answers)


def output(dictionary, template):
    print(dedent(template).format(**dictionary).strip('\n'))
    print()


if __name__ == '__main__':
    main()
