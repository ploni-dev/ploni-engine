# Vendored: dicta-il/dictabert-joint model code

The four Python files in this folder are copied byte for byte from
https://huggingface.co/dicta-il/dictabert-joint at commit
`7b1256fc0846e22d1af431eae299e2dcecee2778`. They are the code the model card asks to be run
through `trust_remote_code`. Here they are loaded from this folder instead, so nothing is
fetched or executed from the hub at run time.

License: CC BY 4.0 (`license: cc-by-4.0` in the front matter of the model card at that
commit). Authors: DICTA, the Israel Center for Text Analysis. No change was made to the files.

`tests/test_vendored.py` pins the SHA-256 of each file. That test shows the files have not
changed since they were copied. It does not show they match the hub, and the download script
no longer fetches `*.py`, so a fresh download cannot show it either. To check them against
the hub, fetch each file at the pinned commit and compare its SHA-256 with the test's:

```
https://huggingface.co/dicta-il/dictabert-joint/resolve/7b1256fc0846e22d1af431eae299e2dcecee2778/<file name>
```

To update, copy the files from a new pinned commit, read the diff, and update the hashes and
this notice in the same change.

The weights are not here. They stay in `models/`, outside the repository.
