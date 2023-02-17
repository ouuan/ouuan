const { readFileSync, writeFileSync } = require('fs');

const feed = JSON.parse(readFileSync('feed.json'));

const posts = feed.items.slice(0, 5).map((item) => `-   ${item.date_modified.split('T')[0]} [${item.title}](${item.url}?utm_source=GitHubProfile)`);

let readme = readFileSync('README.md', 'utf-8');
readme = readme.replace(/(?<=<!--START_SECTION:blog-posts-->\n)[\s\S]*(?=\n<!--END_SECTION:blog-posts-->)/, posts.join('\n'));
writeFileSync('README.md', readme);
