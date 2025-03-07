class Reclaimed < Formula
  include Language::Python::Virtualenv

  desc "A powerful disk usage analyzer with iCloud support"
  homepage "https://github.com/taylorwilsdon/reclaimed"
  version "0.2.0"
  url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v#{version}.tar.gz"
  sha256 "290a5c386634b089da91823789c81024dcd2a9e30c32fa3c0c0542ed76e7db10"
  license "MIT"

  depends_on "python@3.11"
  
  # Runtime dependencies only - no build dependencies needed
  resource "click" do
    url "https://files.pythonhosted.org/packages/b9/2e/0090cbf739cee7d23781ad4b89a9894a41538e4fcf4c31dcdd705b78eb8b/click-8.1.8.tar.gz"
    sha256 "290a5c386634b089da91823789c81024dcd2a9e30c32fa3c0c0542ed76e7db10"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/ab/3a/0316b28d0761c6734d6bc14e770d85506c986c85ffb239e688eeaab2c2bc/rich-13.9.4.tar.gz"
    sha256 "290a5c386634b089da91823789c81024dcd2a9e30c32fa3c0c0542ed76e7db10"
  end

  resource "textual" do
    url "https://files.pythonhosted.org/packages/41/62/4af4689dd971ed4fb3215467624016d53550bff1df9ca02e7625eec07f8b/textual-2.1.2.tar.gz"
    sha256 "290a5c386634b089da91823789c81024dcd2a9e30c32fa3c0c0542ed76e7db10"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"reclaimed", "--help"
  end
end
