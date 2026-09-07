class Brew2port < Formula
  include Language::Python::Virtualenv
  desc "Safe Homebrew to MacPorts migration planner"
  homepage "https://github.com/tomck/brew2port"
  url "https://github.com/tomck/homebrew-brew2port/archive/refs/tags/v0.1.9.tar.gz"
  sha256 "1302dc9651a195278ff1b1ea6a9e99a238c8f262574830e50539e56bdbbbb7fc"
  license "MIT"
  depends_on "python@3.14"

def install
  libexec.install "brew2port"

  (bin/"brew2port").write <<~EOS
    #!/bin/sh
    export PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}"
    exec "#{Formula["python@3.14"].opt_bin}/python3.14" -m brew2port "$@"
  EOS
  chmod 0755, bin/"brew2port"
end

  test do
    system bin/"brew2port", "--help"
  end
end
