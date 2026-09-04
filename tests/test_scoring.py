import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("techticker_update", ROOT / "scripts" / "update.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def ev(weight, multiplier):
    return {"weight": weight, "multiplier": multiplier}


class ScoringTests(unittest.TestCase):
    def test_all_clear_low_readiness(self):
        events=[ev(20,0),ev(15,0),ev(15,0),ev(20,0),ev(15,0),ev(15,0)]
        fred={"semiconductor_ppi":{"chg_3m_pct":8},"storage_device_ppi":{"chg_3m_pct":6}}
        out=mod.compute_scores(events,fred,{"available":True,"score":0})
        self.assertEqual(out["downturn_readiness"],0.0)
        self.assertEqual(out["phase"],"主升／供給吃緊")

    def test_all_triggered_high_readiness(self):
        events=[ev(20,1),ev(15,1),ev(15,1),ev(20,1),ev(15,1),ev(15,1)]
        fred={"semiconductor_ppi":{"chg_3m_pct":-8},"storage_device_ppi":{"chg_3m_pct":-9}}
        out=mod.compute_scores(events,fred,{"available":True,"score":100})
        self.assertEqual(out["downturn_readiness"],100.0)
        self.assertEqual(out["phase"],"深度去庫存／崩價")

    def test_watch_half_weight(self):
        events=[ev(20,.5),ev(15,0),ev(15,.5),ev(20,.5),ev(15,0),ev(15,.5)]
        out=mod.compute_scores(events,{}, {"available":False,"score":None})
        self.assertEqual(out["event_score"],35.0)


if __name__ == "__main__":
    unittest.main()
