-- Bookstore database schema + sample data
-- Backs the Rest_BookStore_DB Flogo app (GET /books/{BookId})

CREATE TABLE IF NOT EXISTS books (
    book_id VARCHAR(20) PRIMARY KEY,
    title   VARCHAR(255) NOT NULL,
    author  VARCHAR(255) NOT NULL
);

INSERT INTO books (book_id, title, author) VALUES
    ('B001', 'The Pragmatic Programmer',        'Andrew Hunt, David Thomas'),
    ('B002', 'Clean Code',                        'Robert C. Martin'),
    ('B003', 'Designing Data-Intensive Applications', 'Martin Kleppmann'),
    ('B004', 'The Go Programming Language',       'Alan Donovan, Brian Kernighan'),
    ('B005', 'Refactoring',                       'Martin Fowler')
ON CONFLICT (book_id) DO UPDATE
    SET title = EXCLUDED.title,
        author = EXCLUDED.author;
