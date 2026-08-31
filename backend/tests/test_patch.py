from pathlib import Path

import pytest

from app.tools.patch import PatchError, apply_patch


def test_apply_patch_modify(tmp_path: Path):
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    target = tmp_path / "Core" / "Src" / "main.c"
    target.write_text("int a = 1;\nint b = 2;\n", encoding="utf-8")
    patch = """--- a/Core/Src/main.c
+++ b/Core/Src/main.c
@@ -1,2 +1,2 @@
-int a = 1;
+int a = 3;
 int b = 2;
"""
    apply_patch(tmp_path, "Core/Src/main.c", patch)
    assert "int a = 3;" in target.read_text(encoding="utf-8")


def test_apply_patch_mismatch(tmp_path: Path):
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Core" / "Src" / "main.c").write_text("hello\n", encoding="utf-8")
    patch = """@@ -1,1 +1,1 @@
-world
+other
"""
    with pytest.raises(PatchError) as e:
        apply_patch(tmp_path, "Core/Src/main.c", patch)
    assert "PATCH_FAILED" in str(e.value)
