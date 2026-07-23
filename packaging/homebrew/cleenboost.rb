# typed: false
# frozen_string_literal: true

# CleanBoost installs a zero-dependency Python CLI that safely cleans
# system, browser and game caches on Windows and macOS.
class Cleanboost < Formula
  include Language::Python::Virtualenv

  desc "Fast safe system + game cache cleaner for Windows and macOS"
  homepage "https://github.com/Freebuff/cleanboost"
  url "https://files.pythonhosted.org/packages/source/c/cleanboost/cleanboost-3.1.1.tar.gz"
  sha256 "ab3a97fe73a5910f42e86602b7acb154de9a30723a8415f4687da9344fcf106c"
  license "MIT"

  livecheck do
    url :homepage
    strategy :github_latest
  end

  depends_on "python@3.12"

  resource "pip" do
    url "https://files.pythonhosted.org/packages/source/p/pip/pip-24.0.tar.gz"
    sha256 "ea9bd1a847e8c5774a5777bb398c19e80bcd4e2aa16a4b301b718fe6f593aba2"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/cleanboost --version")
  end
end
