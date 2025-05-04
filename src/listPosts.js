const { readFileSync, writeFileSync } = require('fs');
const path = require('path');

// --- Configuration ---
const FEED_FILE = 'feed.json';
const README_FILE = 'README.md';
const BLOG_POSTS_SECTION_START = '';
const BLOG_POSTS_SECTION_END = '';
const NUM_POSTS_TO_DISPLAY = 5;
const UTM_SOURCE = 'GitHubProfile';
const DATE_FORMAT = 'YYYY-MM-DD'; // You might need a date formatting library for more complex formats

// --- Helper Functions ---

/**
 * Reads a file and returns its content as a string.
 * @param {string} filePath - The path to the file.
 * @returns {string|null} The file content or null if an error occurs.
 */
const readFileContent = (filePath) => {
  try {
    return readFileSync(filePath, 'utf-8');
  } catch (error) {
    console.error(`Error reading file ${filePath}:`, error.message);
    return null;
  }
};

/**
 * Writes content to a file.
 * @param {string} filePath - The path to the file.
 * @param {string} content - The content to write.
 */
const writeFileContent = (filePath, content) => {
  try {
    writeFileSync(filePath, content);
    console.log(`${path.basename(filePath)} updated successfully.`);
  } catch (error) {
    console.error(`Error writing to file ${filePath}:`, error.message);
  }
};

/**
 * Extracts blog posts from the feed data.
 * @param {object} feed - The parsed feed object.
 * @param {number} limit - The maximum number of posts to extract.
 * @returns {string[]} An array of formatted blog post strings.
 */
const extractBlogPosts = (feed, limit) => {
  if (!feed || !feed.items || !Array.isArray(feed.items)) {
    console.error('Error: Invalid feed.json format. Expected an object with an "items" array.');
    return [];
  }

  return feed.items
    .slice(0, limit)
    .map((item) => {
      const datePart = item.date_modified ? formatDate(item.date_modified, DATE_FORMAT) : 'N/A';
      const title = item.title || 'Untitled';
      const url = item.url || '#';
      return `-   ${datePart} [${title}](${url}?utm_source=${UTM_SOURCE})`;
    });
};

/**
 * Updates the blog posts section in the README file.
 * @param {string} readmeContent - The current content of the README file.
 * @param {string[]} blogPosts - An array of formatted blog post strings.
 * @returns {string} The updated README content.
 */
const updateReadmeContent = (readmeContent, blogPosts) => {
  const startMarker = readmeContent.indexOf(BLOG_POSTS_SECTION_START);
  const endMarker = readmeContent.indexOf(BLOG_POSTS_SECTION_END);

  if (startMarker === -1 || endMarker === -1 || startMarker >= endMarker) {
    console.error(`Error: Could not find the blog posts section markers (${BLOG_POSTS_SECTION_START} and ${BLOG_POSTS_SECTION_END}) in ${README_FILE}.`);
    return readmeContent;
  }

  const contentToReplace = readmeContent.substring(startMarker + BLOG_POSTS_SECTION_START.length, endMarker);
  const newContent = `\n${blogPosts.join('\n')}\n`;
  return readmeContent.replace(contentToReplace, newContent);
};

/**
 * Formats a date string into a specific format.
 * @param {string} dateString - The date string to format (e.g., '2023-10-26T10:00:00Z').
 * @param {string} format - The desired format ('YYYY-MM-DD' is currently supported).
 * @returns {string} The formatted date string or the original string if formatting fails.
 */
const formatDate = (dateString, format) => {
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      console.warn(`Warning: Invalid date string: ${dateString}`);
      return dateString.split('T')[0] || dateString; // Basic fallback
    }
    switch (format) {
      case 'YYYY-MM-DD':
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
      default:
        console.warn(`Warning: Unsupported date format: ${format}. Using basic split.`);
        return dateString.split('T')[0] || dateString;
    }
  } catch (error) {
    console.error('Error formatting date:', error.message);
    return dateString.split('T')[0] || dateString; // Basic fallback
  }
};

/**
 * Checks if the feed.json file exists.
 * @returns {boolean} True if the file exists, false otherwise.
 */
const checkIfFeedExists = () => {
  return fs.existsSync(FEED_FILE);
};

/**
 * Checks if the README.md file exists.
 * @returns {boolean} True if the file exists, false otherwise.
 */
const checkIfReadmeExists = () => {
  return fs.existsSync(README_FILE);
};

/**
 * Logs a message to the console indicating the start of the script.
 */
const logScriptStart = () => {
  console.log('--- Starting README Blog Post Updater ---');
};

/**
 * Logs a message to the console indicating the end of the script.
 */
const logScriptEnd = () => {
  console.log('--- README Blog Post Updater Finished ---');
};

// --- Main Execution ---
const fs = require('fs'); // Moved require('fs') here to be available for checkIfFileExists

logScriptStart();

if (!checkIfFeedExists()) {
  console.error(`Error: ${FEED_FILE} not found. Please ensure the feed file exists in the same directory.`);
  process.exit(1);
}

if (!checkIfReadmeExists()) {
  console.error(`Error: ${README_FILE} not found. Please ensure the README file exists in the same directory.`);
  process.exit(1);
}

try {
  const feedContent = readFileContent(FEED_FILE);
  if (!feedContent) {
    process.exit(1); // Exit if feed reading fails
  }

  const feed = JSON.parse(feedContent);
  const blogPosts = extractBlogPosts(feed, NUM_POSTS_TO_DISPLAY);

  const readmeContent = readFileContent(README_FILE);
  if (!readmeContent) {
    process.exit(1); // Exit if README reading fails
  }

  const updatedReadme = updateReadmeContent(readmeContent, blogPosts);
  writeFileContent(README_FILE, updatedReadme);

} catch (error) {
  console.error('An unexpected error occurred:', error.message);
  process.exit(1); // Exit on unexpected errors
} finally {
  logScriptEnd();
}
