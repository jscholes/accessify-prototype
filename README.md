# accessify

Accessify is a screen reader-accessible control interface for Spotify on Windows.

Note: This code represents a prototype, written in Python.  Please go to https://github.com/jscholes/accessify for updated code.

## Running the code

The software is still in its pre-alpha stages, but if you wish to run it and try it out, here's what you'll need to do:

First, install Python 3.6.1 (32-bit) from the official Python website.  Make sure it's added to your PATH, which is most likely the default.  Any lower version will not work.  You'll also need a Windows-compatible version of Git.

Once that's done, create a directory to hold the project somewhere on your system:

    > md accessify
    > cd accessify

Create a virtual environment:

    > virtualenv env
    > env\scripts\activate

Clone the repository:

    > git clone https://github.com/jscholes/accessify

Install the dependencies:

    > cd accessify
    > dev-setup.bat

Run it:

    > accessify

At this point, you should see the message:

> Please ensure the environment variables SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set.

For now, I'll leave the rest up to you.  I'll update this README with more detailed instructions when the code for authorising your Spotify account from the GUI is actually written, as at the moment the process is barely even developer-friendly.  The project is runnable, though, if you can find and fill in the required information.  You'll need a Spotify client ID and secret, plus an access token and refresh token.  Good luck!