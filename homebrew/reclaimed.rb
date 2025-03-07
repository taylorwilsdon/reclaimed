class Reclaimed < Formula
  include Language::Python::Virtualenv

  desc "A powerful disk usage analyzer with iCloud support"
  homepage "https://github.com/taylorwilsdon/reclaimed"
  version "0.1.6"
  url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v#{version}.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA" # Update this with the actual SHA after creating a release
  license "MIT"

  depends_on "python@3.11"

  resource "click" do
    url "https://files.pythonhosted.org/packages/96/d3/f04c7bfcf5c1862a2a5b845c6b2b360488cf47af55dfa79c98f6a6bf98b5/click-8.1.7.tar.gz"
    sha256 "ca9853ad459e787e2192211578cc907e7594e294c7ccc834310722b41b9ca6de"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/a7/ec/4a7d80728bd429f7c0d4d51245287158a1516315cadbb146012439403a9d/rich-13.7.0.tar.gz"
    sha256 "5cb5123b5cf9ee70584244246816e9114227e0b98ad9176eede6ad54bf5403fa"
  end

  resource "textual" do
    url "https://files.pythonhosted.org/packages/8c/d1/3a2bce3cee40c836e0e2ea0bf49e7a8f3d60dafaf57b6d8a1b3c9b4f3dc7/textual-0.52.1.tar.gz"
    sha256 "6dad6ecf0a8b7a3c5c9a8dcd1d7e2e0a5b9b1a4e85d4f33e275a66f9450b0c4f"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"reclaimed", "--help"
  end
end
