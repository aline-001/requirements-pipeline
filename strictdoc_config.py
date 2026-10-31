"""StrictDoc 0.30.x project configuration (replaces the deprecated strictdoc.toml)."""

from strictdoc.core.project_config import ProjectConfig, ProjectFeature


def create_config() -> ProjectConfig:
    return ProjectConfig(
        project_title="Requirements Engineering Pipeline",
        project_features=[
            ProjectFeature.TABLE_SCREEN,
            ProjectFeature.TRACEABILITY_SCREEN,
            ProjectFeature.DEEP_TRACEABILITY_SCREEN,
            ProjectFeature.TRACEABILITY_MATRIX_SCREEN,
            ProjectFeature.SEARCH,
            # Shows src/ functions tagged @relation(REQ-xxx, scope=function)
            # next to the requirements they implement.
            ProjectFeature.REQUIREMENT_TO_SOURCE_TRACEABILITY,
            ProjectFeature.SOURCE_FILE_LANGUAGE_PARSERS,
        ],
        include_doc_paths=["docs/sdoc/**"],
        include_source_paths=["src/**"],
    )
