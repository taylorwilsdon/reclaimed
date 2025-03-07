class Reclaimed < Formula
  include Language::Python::Virtualenv

  desc "A powerful disk usage analyzer with iCloud support"
  homepage "https://github.com/taylorwilsdon/reclaimed"
  version "0.1.7"
  url "https://github.com/taylorwilsdon/reclaimed/archive/refs/tags/v#{version}.tar.gz"
  sha256 "4831097bbffd108dcc088ddd6a3aa6a9c6d5c01ffbe2cccfc98dbec755f7cb70"
  license "MIT"

  depends_on "python@3.11"
  
  # Build dependencies
  resource "hatchling" do
    url "https://files.pythonhosted.org/packages/8f/8a/cc1debe3514da292094f1c3a700e4ca25442489731ef7c0814358816bb03/hatchling-1.27.0.tar.gz"
    sha256 "971c296d9819abb3811112fc52c7a9751c8d381898f36533bb16f9791e941fd6"
  end

  resource "hatch-vcs" do
    url "https://files.pythonhosted.org/packages/f5/c9/54bb4fa27b4e4a014ef3bb17710cdf692b3aa2cbc7953da885f1bf7e06ea/hatch_vcs-0.4.0.tar.gz"
    sha256 "093810748fe01db0d451fabcf2c1ac2688caefd232d4ede967090b1c1b07d9f7"
  end

  resource "setuptools-scm" do
    url "https://files.pythonhosted.org/packages/4b/bd/c5d16dd95900567e09744af92119da7abc5f447320d53ec1d9415ec30263/setuptools_scm-8.2.0.tar.gz"
    sha256 "a18396a1bc0219c974d1a74612b11f9dce0d5bd8b1dc55c65f6ac7fd609e8c28"
  end

  # Runtime dependencies
  resource "click" do
    url "https://files.pythonhosted.org/packages/b9/2e/0090cbf739cee7d23781ad4b89a9894a41538e4fcf4c31dcdd705b78eb8b/click-8.1.8.tar.gz"
    sha256 "ed53c9d8990d83c2a27deae68e4ee337473f6330c040a31d4225c9574d16096a"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/ab/3a/0316b28d0761c6734d6bc14e770d85506c986c85ffb239e688eeaab2c2bc/rich-13.9.4.tar.gz"
    sha256 "439594978a49a09530cff7ebc4b5c7103ef57baf48d5ea3184f21d9a2befa098"
  end

  resource "textual" do
    url "https://files.pythonhosted.org/packages/41/62/4af4689dd971ed4fb3215467624016d53550bff1df9ca02e7625eec07f8b/textual-2.1.2.tar.gz"
    sha256 "aae3f9fde00c7440be00e3c3ac189e02d014f5298afdc32132f93480f9e09146"
  end

  def install
    # Set static version for build since we don't have git metadata in the tarball
    ENV["SETUPTOOLS_SCM_PRETEND_VERSION"] = version
    virtualenv_install_with_resources
  end

  test do
    system bin/"reclaimed", "--help"
  end
end
