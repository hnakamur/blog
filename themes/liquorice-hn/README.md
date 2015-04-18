# liquorice-hn

Liquorice-hn is a small black and white theme for [Hugo](https://github.com/spf13/hugo) (a fast and modern static website engine).
It is based on [eliasson/liquorice](https://github.com/eliasson/liquorice).


### Dependencies

Liquorice-hn needs at least version 0.12 of Hugo, as it uses features such as partials.


### Partials

There are a few partials that is of great interest to override


#### author

The author partial is added at the end of each single page (such as blog posts) and by default only prints the name of the author registered in the site params, e.g. in your `config.toml`

    [params]
        author = "Hiroaki Nakamura"
        author_link = "https://hnakamur.github.io"

In order to override and have your own markup appended to single pages, just create the file `layouts/partials/author.html` and roll your own.


### Shortcodes

Liquorice-hn comes with these additional shortcodes:


#### gist

Include a Github gist using their JavaScript include.

    {{% gist e572b28c9a0eef0b2763 %}}

Where the first parameter is the gist id.


### Building

There is not much to build, but the theme CSS is minified using the node tool [clean-css](https://github.com/GoalSmashers/clean-css).

    cleancss -o static/css/liquorice.min.css static/css/liquorice.css

*Any change in styles needs to result in a minification!*

#### build with npm run

For the first time, run the command below to install `clean-css`.

```
npm install
```

Run the command below to minify the theme CSS.

```
npm build
```

# License

Liquorice-hn is released under the MIT license, see LICENSE for details.
