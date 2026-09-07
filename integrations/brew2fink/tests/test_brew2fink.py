import json
import tempfile
import unittest
from brew2fink.catalog import load
from brew2fink.core import plan, install

class TestBrew2Fink(unittest.TestCase):
    def test_catalog_and_near_hit_are_review_only(self):
        data={"relations":[{"source":{"manager":"homebrew","package_type":"formula","native_name":"ansible@12"},"target":{"manager":"fink","package_type":"package","native_name":"ansible"},"confidence":0.78,"matching_method":"version-family","review_status":"needs-review"}]}
        with tempfile.NamedTemporaryFile(mode="w") as stream:
            json.dump(data,stream); stream.flush()
            rows=plan([{"kind":"formula","name":"ansible@12"}],load(stream.name))
        self.assertEqual(install(rows)[0]["status"],"needs-review")
