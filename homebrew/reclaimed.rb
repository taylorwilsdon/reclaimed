class Reclaimed < Formula
  include Language::Python::Virtualenv

  desc "A powerful disk usage analyzer with iCloud support"
  homepage "https://github.com/taylorwilsdon/reclaimed"
  version "0.1.6"
  url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v#{version}.tar.gz"
  sha256 "5baacc4076063c649a9f143182f1af9370fedcbef15de777da0a6782ce24839b" # Will be updated by release script
  license "MIT"

  depends_on "python@3.11"
  
  # Add all dependencies from pyproject.toml

  resource "click" do
    url "https://files.pythonhosted.org/packages/96/d3/f04c7bfcf5c1862a2a5b845c6b2b360488cf47af55dfa79c98f6a6bf98b5/click-8.1.7.tar.gz"
    sha256 "ca9853ad459e787e2192211578cc907e7594e294c7ccc834310722b41b9ca6de"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/a7/ec/4a7d80728bd429f7c0d4d51245287158a1516315cadbb146012439403a9d/rich-13.7.0.tar.gz"
    sha256 "5cb5123b5cf9ee70584244246816e9114227e0b98ad9176eede6ad54bf5403fa"
  end

  resource "textual" do
    url "https://files.pythonhosted.org/packages/b5/a8/6a1a0f9a0d1d89e7a9b1a0e6f8d7b8f6a0fafbbc0b8c3f392b4b9ef9e45a/textual-0.52.1.tar.gz"
    sha256 "08dc36c19550ef75a9e2cb2c2c7d51e8f8d2a1d7da0c9f6c6389b7e65a7cd09a"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"reclaimed", "--help"
  end
end
