class Reclaimed < Formula
  include Language::Python::Virtualenv

  desc "Powerful disk usage analyzer with iCloud support"
  homepage "https://github.com/taylorwilsdon/reclaimed"
  url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
  sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  license "MIT"

  depends_on "python"

  # Runtime dependencies only - no build dependencies needed
  resource "click" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "rich" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "textual" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "typing-extensions" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "linkify-it-py" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "markdown-it-py" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "mdit-py-plugins" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "mdurl" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "platformdirs" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "pygments" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  resource "uc-micro-py" do
    url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v0.2.8.tar.gz"
    sha256 "63ac4ed58630dcd78d06a2d802dbec276c4c6808c431cfdfc4f372aece2e26b3"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"reclaimed", "--help"
  end
end
