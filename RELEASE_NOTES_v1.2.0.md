# Pastify v1.2.0 — Infrastructure & Platform Improvements

## Highlights

- Migrated processed PDF archives from public GitHub Releases to private, access-controlled GitHub Releases storage.
- Added authenticated server-side PDF retrieval through Streamlit Secrets.
- Removed the previous publicly accessible bulk PDF archives.
- Improved the About Us page with founder profiles and LinkedIn/GitHub links.
- Updated README documentation to reflect the current deployment architecture.

## Security and deployment

- PDF storage credentials remain outside the public source repository.
- The Streamlit deployment uses the `hosting-ready` branch.
- The private PDF storage release tag is separate from the public application version.

## Copyright

Pastify is an independent educational project and is not affiliated with or endorsed by Cambridge International. Written permission to display Cambridge examination materials has been requested and remains pending. Private storage does not itself grant permission to display or redistribute copyrighted materials.

## Previous release

v1.1.0 — MCQ Expansion.
