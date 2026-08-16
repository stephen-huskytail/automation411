import io
import unittest
from pathlib import Path

from PIL import Image

import huskytail_gmb


class HuskyTailBrandMediaTests(unittest.TestCase):
    def test_all_pillars_render_a_brand_controlled_jpeg(self):
        for pillar in huskytail_gmb.PILLARS:
            with self.subTest(pillar=pillar):
                image = Image.open(io.BytesIO(huskytail_gmb.render_huskytail_brand_media(pillar)))
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.size, (1536, 1024))
                self.assertEqual(image.mode, "RGB")

    def test_rejects_unknown_pillar_before_any_external_action(self):
        with self.assertRaisesRegex(ValueError, "Unknown HuskyTail media pillar"):
            huskytail_gmb.render_huskytail_brand_media("unknown")

    def test_publisher_does_not_use_ai_generated_media(self):
        source = Path(huskytail_gmb.__file__).read_text(encoding="utf-8")
        self.assertNotIn("generate_image(", source)


if __name__ == "__main__":
    unittest.main()
