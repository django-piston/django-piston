This is a bare-skeleton Django application which demonstrates how you can
add an API to your own applications.

It's a simple blog application, with a "Blogpost" model, with an API on top
of it. It has a fixture which contains a sample user (used as author and 
for auth) and a couple of posts.

You can get started like so:

$ python manage.py syncdb (answer "no" when it asks for superuser creation)
$ python manage.py runserver

Now, the test user has authentication info:

Username: testuser
Password: foobar

The API is accessible via '/api/posts'. You can try it with curl:

$ curl -u testuser:foobar "http://127.0.0.1:8000/api/posts/?format=yaml"
- author: {absolute_uri: /users/testuser/, username: testuser}
  content: This is just a sample post.
  content_length: 27
  created_on: 2009-04-27 04:55:23
  title: Sample blogpost 1
- author: {absolute_uri: /users/testuser/, username: testuser}
  content: This is yet another sample post.
  content_length: 32
  created_on: 2009-04-27 04:55:33
  title: Another sample post

That's an authorized request, and the user gets back privileged information.

Anonymously:

$ curl "http://127.0.0.1:8000/api/posts/?format=yaml" 
- {content: This is just a sample post., created_on: !!timestamp '2009-04-27 04:55:23',
  title: Sample blogpost 1}
- {content: This is yet another sample post., created_on: !!timestamp '2009-04-27
    04:55:33', title: Another sample post}

You can check out how this is done in the 'api' directory.

Also, there's plenty of documentation on http://bitbucket.org/jespern/django-piston/

Have fun!