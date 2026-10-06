from cli_args import cli_project_path, resolve_cli_project_path


def test_cli_project_path_flag_and_bare_json():
    json_path = r"\\fileserver\QA\Morning QA\case\vtk_image_labeler_3d.project.json"
    assert cli_project_path(["app", "--project", json_path]) == json_path
    assert cli_project_path(["app", "--project=" + json_path]) == json_path
    assert cli_project_path(["app", json_path]) == json_path
    assert cli_project_path(["app", "--smoke-test"]) is None
    assert cli_project_path(["app"]) is None


def test_resolve_cli_project_path(tmp_path):
    dest = tmp_path / "vtk_image_labeler_3d.project.json"
    dest.write_text("{}\n", encoding="utf-8")
    resolved = resolve_cli_project_path(["ImageLabeler3D.exe", "--project", str(dest)])
    assert resolved == str(dest.resolve())
