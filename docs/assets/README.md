# Assets

## `hero.jpg`

The header illustration. Generated with ChatGPT by the repository owner, who
therefore holds the rights to it; it ships under the same MIT licence as the
rest of the repository. Recorded here because the provenance of a generated
asset is invisible once it is just a file in a folder, and someone will ask.

Cropped from a portrait original to a 1122×604 band across the three heads: a
portrait hero at full README width pushes every word of documentation below the
fold.

No title is baked into it. GitHub renders the heading directly underneath, text
inside an image is invisible to search and to screen readers, and a tagline in a
raster file has to be re-rendered rather than edited.

## `logo.svg`

The mark: one ring carrying three heads. Every head's base sits at radius 29
against a ring spanning 28–32, so the heads fuse into the ring rather than
piercing it — an earlier version had them starting inside the ring and the
junctions looked like mistakes.

The centre is deliberately empty. A gate is something you get through, not a
filled badge.

## Palette

The three colours are **sampled from the eyes in `hero.jpg`**, not chosen to
look similar. Each one is a stage:

| Stage | Colour    | Head on the artwork | Meaning                    |
|-------|-----------|---------------------|----------------------------|
| 0     | `#78BC28` | centre, green       | enumerate the behaviour    |
| 1     | `#ECAE26` | left, amber         | break the code             |
| 2     | `#F03C27` | right, red          | break it past the boundary |

Sampling took three attempts: the first two picked up the yellow-green glow
around the pupils and returned an olive that matched nothing. The working method
filters candidate pixels by hue range and takes the median of the brightest,
most saturated ones.

The ordering is a gradient from calm to alarming, and it happens to run
left-to-right across the artwork — but the mapping is by **colour**, not by
position, which is why the green head standing in the centre is not a problem.
