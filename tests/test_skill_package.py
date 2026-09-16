import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillPackageTests(unittest.TestCase):
    def test_skill_frontmatter_has_required_identity(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertRegex(frontmatter, r"(?m)^name: project-cognitive-cache$")
        self.assertRegex(frontmatter, r"(?m)^description: \S.+$")

    def test_openai_metadata_has_interface_and_invocation_policy(self):
        text = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("interface:", text)
        self.assertIn('display_name: "Project Cognitive Cache"', text)
        self.assertIn("allow_implicit_invocation: true", text)

    def test_readme_local_markdown_links_exist(self):
        for readme_name in ("README.md", "README.zh-CN.md"):
            text = (SKILL_ROOT / readme_name).read_text(encoding="utf-8")
            for target in re.findall(r"\[[^]]+\]\((?!https?://)([^)#]+)(?:#[^)]+)?\)", text):
                with self.subTest(readme=readme_name, target=target):
                    self.assertTrue((SKILL_ROOT / target).exists())


if __name__ == "__main__":
    unittest.main()
