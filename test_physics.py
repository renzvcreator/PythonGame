"""Unit tests for the projectile-motion module and the game rules that depend on it.

Run with:  python -m unittest discover tests
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics_hoops import physics as P  # noqa: E402
from physics_hoops.entities import Hoop, Obstacle, Projectile  # noqa: E402
from physics_hoops.scoring import calculate_score, calculate_accuracy_bonus  # noqa: E402
from physics_hoops.levels import LEVELS  # noqa: E402


class TestCoreEquations(unittest.TestCase):
    def test_velocity_components_45_degrees(self):
        vx, vy = P.calculate_velocity_components(18.0, 45.0)
        self.assertAlmostEqual(vx, 12.73, places=2)
        self.assertAlmostEqual(vy, 12.73, places=2)

    def test_flight_time_range_and_height_from_ground(self):
        vx, vy = P.calculate_velocity_components(18.0, 45.0)
        t = P.calculate_flight_time(0.0, vy)
        self.assertAlmostEqual(t, 2.595, places=2)                      # 2 Vy / g
        self.assertAlmostEqual(P.calculate_range(vx, t), 33.03, places=1)  # V0^2 sin(2 theta) / g
        self.assertAlmostEqual(P.calculate_maximum_height(0.0, vy), 8.26, places=2)

    def test_position_matches_equations(self):
        x, y = P.calculate_projectile_position(1.0, 2.0, 10.0, 5.0, 1.0)
        self.assertAlmostEqual(x, 11.0)
        self.assertAlmostEqual(y, 2.0 + 5.0 - 0.5 * 9.81)

    def test_velocity_at_time(self):
        vx, vy = P.calculate_velocity_at_time(10.0, 5.0, 2.0)
        self.assertAlmostEqual(vx, 10.0)      # no horizontal acceleration without wind
        self.assertAlmostEqual(vy, 5.0 - 2 * 9.81)

    def test_times_at_height(self):
        vx, vy = P.calculate_velocity_components(12.0, 60.0)
        times = P.calculate_times_at_height(2.0, vy, 4.0)
        self.assertIsNotNone(times)
        for t in times:
            _, y = P.calculate_projectile_position(0, 2.0, vx, vy, t)
            self.assertAlmostEqual(y, 4.0, places=6)
        self.assertIsNone(P.calculate_times_at_height(2.0, vy, 50.0))

    def test_required_velocity_hits_target(self):
        x0, y0, tx, ty, angle = 1.5, 2.0, 10.0, 3.05, 45.0
        v = P.calculate_required_velocity(x0, y0, tx, ty, angle)
        vx, vy = P.calculate_velocity_components(v, angle)
        t = (tx - x0) / vx
        _, y = P.calculate_projectile_position(x0, y0, vx, vy, t)
        self.assertAlmostEqual(y, ty, places=6)

    def test_required_angles_hit_target(self):
        x0, y0, tx, ty, v = 1.5, 2.0, 15.0, 3.05, 14.0
        angles = P.calculate_required_angles(x0, y0, tx, ty, v)
        self.assertEqual(len(angles), 2)
        for a in angles:
            vx, vy = P.calculate_velocity_components(v, a)
            t = (tx - x0) / vx
            _, y = P.calculate_projectile_position(x0, y0, vx, vy, t)
            self.assertAlmostEqual(y, ty, places=4)

    def test_predict_flight_matches_closed_form(self):
        pred = P.predict_flight(1.5, 2.0, 15.0, 40.0)
        vx, vy = P.calculate_velocity_components(15.0, 40.0)
        self.assertAlmostEqual(pred.flight_time, P.calculate_flight_time(2.0, vy))
        self.assertAlmostEqual(pred.max_height, P.calculate_maximum_height(2.0, vy))
        self.assertAlmostEqual(pred.points[-1][2], 0.0, places=9)

    def test_drag_shortens_range(self):
        ideal = P.predict_flight(1.5, 2.0, 20.0, 45.0)
        with_drag = P.predict_flight(1.5, 2.0, 20.0, 45.0, P.Environment(drag_k=P.BASKETBALL_DRAG_K))
        self.assertLess(with_drag.range, ideal.range)
        self.assertLess(with_drag.max_height, ideal.max_height)


class TestProjectileEntity(unittest.TestCase):
    def test_frame_stepping_follows_equations(self):
        ball = Projectile(1.5, 2.0, 12.0, 50.0)
        for _ in range(120):
            ball.update(1 / 120)
        vx, vy = P.calculate_velocity_components(12.0, 50.0)
        x, y = P.calculate_projectile_position(1.5, 2.0, vx, vy, 1.0)
        self.assertAlmostEqual(ball.x, x, places=6)
        self.assertAlmostEqual(ball.y, y, places=6)
        self.assertAlmostEqual(ball.vy, vy - 9.81, places=6)


class TestHoopAndObstacles(unittest.TestCase):
    def test_ball_dropping_through_centre_scores(self):
        hoop = Hoop(10.0, 3.05)
        res, xc = hoop.check_scoring(9.9, 3.2, 10.1, 2.9, 0.4)
        self.assertEqual(res, 'made')
        self.assertAlmostEqual(xc, 10.0, places=6)

    def test_ball_rising_through_rim_does_not_score(self):
        hoop = Hoop(10.0, 3.05)
        res, _ = hoop.check_scoring(10.0, 2.9, 10.0, 3.2, 0.4)
        self.assertEqual(res, 'under')

    def test_ball_hitting_rim_edge_is_not_a_score(self):
        hoop = Hoop(10.0, 3.05)
        res, _ = hoop.check_scoring(hoop.right, 3.2, hoop.right, 2.9, 0.4)
        self.assertEqual(res, 'rim')

    def test_ball_far_away_is_passed(self):
        hoop = Hoop(10.0, 3.05)
        res, _ = hoop.check_scoring(5.0, 3.2, 5.0, 2.9, 0.4)
        self.assertEqual(res, 'passed')

    def test_obstacle_collision(self):
        wall = Obstacle(10.0, 0.0, 1.0, 6.0)
        self.assertTrue(wall.collides_circle(9.8, 3.0, 0.4))
        self.assertFalse(wall.collides_circle(9.0, 3.0, 0.4))
        self.assertFalse(wall.collides_circle(10.5, 6.5, 0.4))


class TestScoring(unittest.TestCase):
    def test_breakdown(self):
        b = calculate_score(0.0, 0.65, 1, 3)
        self.assertEqual((b.base, b.accuracy, b.efficiency, b.streak, b.total), (100, 50, 50, 50, 250))
        self.assertEqual(calculate_accuracy_bonus(0.65, 0.65), 0)


class TestLevelsAreSolvable(unittest.TestCase):
    def test_every_level_has_a_shot_within_slider_limits(self):
        for lv in LEVELS:
            lx, ly = lv.launch
            solvable = False
            for angle in range(20, 71):
                v = P.calculate_required_velocity(lx, ly, lv.hoop_x, lv.hoop_y, angle)
                if v is None or not (5.0 <= v <= 30.0):
                    continue
                # simulate to make sure the arc clears every obstacle and arrives falling
                ball = Projectile(lx, ly, v, angle)
                hoop = Hoop(lv.hoop_x, lv.hoop_y)
                ok = None
                for _ in range(120 * 20):
                    ball.update(1 / 120)
                    if any(ob.collides_circle(ball.x, ball.y, ball.radius) for ob in
                           (Obstacle(*o) for o in lv.obstacles)):
                        ok = False
                        break
                    res, _ = hoop.check_scoring(ball.prev_x, ball.prev_y, ball.x, ball.y, ball.radius)
                    if res == 'made':
                        ok = True
                        break
                    if res in ('rim', 'under') or ball.y < 0:
                        ok = False
                        break
                if ok:
                    solvable = True
                    break
            self.assertTrue(solvable, f"Level {lv.number} cannot be made with the slider ranges")


if __name__ == "__main__":
    unittest.main()
