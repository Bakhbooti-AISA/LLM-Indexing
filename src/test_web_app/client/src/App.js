import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import React, { useEffect, useState } from 'react';
import axios from 'axios';

function Home() {
  return (
    <div className="page-wrapper">
      <div className="container">
        <h1>Namaloom Frad</h1>
        <p>This is the official website of Namaloom Frad — a space for sharing thoughts, research, and ideas.</p>
        <p>Here, members discuss books through the <strong>Book Club</strong> and dive into investigations and findings in the <strong>Blogs</strong> section.</p>
        <div className="nav-buttons">
          <Link to="/book-club"><button>Book Club</button></Link>
          <Link to="/blogs"><button>Blogs</button></Link>
        </div>
      </div>
    </div>
  );
}

function BookClub() {
  const books = [
    {
      title: "Trust",
      author: "Hernan Diaz",
      description: "A layered narrative exploring wealth, power, and truth through the lens of 20th-century New York finance.",
      cover: "https://www.goodreads.com/en/book/show/58210933"
    },
    {
      title: "The Three-Body Problem",
      author: "Liu Cixin",
      description: "A mind-bending sci-fi novel that intertwines alien contact and Chinese history in a cosmic struggle.",
      cover: "https://images-na.ssl-images-amazon.com/images/I/81NVrP0lGUL.jpg"
    },
    {
      title: "If I Must Die",
      author: "Refaat Alareer",
      description: "A powerful collection of poetry and prose from Gaza, capturing resistance, love, and pain.",
      cover: "https://m.media-amazon.com/images/I/71wE0TfhvjL._SY522_.jpg"
    },
    {
      title: "Antifragile",
      author: "Nassim Nicholas Taleb",
      description: "An exploration of systems that thrive under stress and chaos — a guide to embracing uncertainty.",
      cover: "https://images-na.ssl-images-amazon.com/images/I/71wY0GVhoQL.jpg"
    },
    {
      title: "The Black Swan",
      author: "Nassim Nicholas Taleb",
      description: "Reveals how unpredictable, rare events shape the world more than we expect — and why we fail to see them coming.",
      cover: "https://images-na.ssl-images-amazon.com/images/I/71lIfvr6wEL.jpg"
    }
  ];

  return (
    <div className="page-wrapper">
      <div className="container">
        <h2>📚 Book Club</h2>
        {books.map((book, index) => (
          <div key={index} className="book">
            <img src={book.cover} alt={book.title} />
            <div>
              <h3>{book.title}</h3>
              <p><em>by {book.author}</em></p>
              <p>{book.description}</p>
            </div>
          </div>
        ))}
        <Link to="/"><button>Back</button></Link>
      </div>
    </div>
  );
}


function Blogs() {
  const [articles, setArticles] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedContent, setSelectedContent] = useState(null);

  useEffect(() => {
    axios.get('/api/articles')
      .then(res => setArticles(res.data))
      .catch(err => console.error('Failed to load articles:', err));
  }, []);

  useEffect(() => {
    if (selectedId) {
      axios.get(`/api/articles/${selectedId}`)
        .then(res => setSelectedContent(res.data))
        .catch(err => console.error('Failed to load article:', err));
    }
  }, [selectedId]);

  return (
    <div className="page-wrapper blog-layout">
      <div className="sidebar">
        <h3>Articles</h3>
        {articles.map(article => (
          <button key={article.id} onClick={() => setSelectedId(article.id)}>
            {article.title}
          </button>
        ))}
      </div>
      <div className="article-content">
        {selectedContent ? (
          <>
            <h2>{selectedContent.title}</h2>
            <p>{selectedContent.body}</p>
          </>
        ) : (
          <p>Select an article from the sidebar.</p>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/book-club" element={<BookClub />} />
        <Route path="/blogs" element={<Blogs />} />
      </Routes>
    </Router>
  );
}

export default App;
