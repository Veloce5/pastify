# Pastify Changelog

All notable updates to Pastify are documented here.

Versions follow Semantic Versioning: MAJOR.MINOR.PATCH.

## [Unreleased]

### Development and maintenance
- Reorganized database and MCQ extraction utilities into `tools/`.
- Added configurable MCQ batch processing with a dry-run preview.
- Preserved historical crop-processing scripts and code backups.
- Organized application assets, screenshots, and migration documentation.
- Added isolated database and PDF storage configuration for MCQ integration testing.
- Updated repository documentation and file paths.

The expanded 19,103-row MCQ integration database is under local validation and is not part of the published v1.1.0 release.

## [1.1.0] — 2026-10-11

### Added
- Added 1,340 multiple-choice questions across the question bank.
- Expanded the question database to 12,383 questions.
- Introduced a What's New page to display product updates and release history.

### Improved
- Improved MCQ PDF processing and question availability.
- Excluded questions without recorded answers from quizzes.

## [1.0.0] — Initial Release

### Added
- Cambridge A-Level past-paper question browsing.
- Worksheet Builder for creating custom practice worksheets.
- Quiz Mode and Timed Test.
- Learning progress tracking.
