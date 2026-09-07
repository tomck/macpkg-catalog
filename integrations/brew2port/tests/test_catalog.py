import json
import tempfile
import unittest
from brew2port.catalog import load_catalog

class TestCatalog(unittest.TestCase):
    def test_loads_confident_and_near_hit_relationships(self):
        data={"relations":[
            {"source":{"manager":"homebrew","package_type":"formula","native_name":"node"},"target":{"manager":"macports","package_type":"port","native_name":"nodejs26"},"confidence":1.0,"matching_method":"curated","review_status":"automatic"},
            {"source":{"manager":"homebrew","package_type":"formula","native_name":"ansible@12"},"target":{"manager":"macports","package_type":"port","native_name":"py313-ansible"},"confidence":0.78,"matching_method":"version-family","review_status":"needs-review"},
        ]}
        with tempfile.NamedTemporaryFile(mode="w") as handle:
            json.dump(data,handle); handle.flush(); table=load_catalog(handle.name)
        self.assertEqual(table[("formula","node")]["candidates"][0]["port"],"nodejs26")
        self.assertEqual(table[("formula","ansible@12")]["candidates"][0]["catalog_status"],"needs-review")
