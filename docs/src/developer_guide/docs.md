# Docs
This website was made using [mdBook](https://github.com/rust-lang/mdBook) and is hosted on [Github Pages](https://pages.github.com/).

## mdBook
[The official mdBook guide](https://rust-lang.github.io/mdBook/) is pretty good and walks you through the entire setup process and how to use it.


First [install rust](https://www.rust-lang.org/tools/install) to get the cargo package manager:
``` bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

install mdbook:
``` bash
cargo install mdbook --version 0.4.52
```

To display latex equations and environments install [mdbook-katex](https://github.com/lzanini/mdbook-katex) with the command:

``` bash
cargo install mdbook-katex
```

Launch mdbook from the AnkiMorphs directory with the command:
``` bash
mdbook serve docs/ --open
```

## Github Pages

To make github automatically deploy the generated book to github pages do the following:
1. [Activate Github Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publishing-with-a-custom-github-actions-workflow): <br> Github repo settings &rarr; Code and automation &rarr; Pages &rarr; Build and deployment &rarr; Github Actions
2. [Make any necessary adjustments](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#creating-a-custom-github-actions-workflow-to-publish-your-site) to branch names or paths in:<br> ```anki-morphs/.github/workflows/deploy.yml```

Project sites will be available at:
```
http(s)://<username>.github.io/<repository>
```


### Styling

For additional spacing between bullet points, you have to add a space between at least one of the points, e.g.:
``` text
* **a**:  
    a
    
* **b**:  
    b
* **c**:  
    c
```


