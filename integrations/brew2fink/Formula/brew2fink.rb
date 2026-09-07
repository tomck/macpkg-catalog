class Brew2fink < Formula
  desc "Safe Homebrew to Fink migration planner"
  homepage "https://github.com/tomck/homebrew-brew2fink"
  url "https://github.com/tomck/homebrew-brew2fink/archive/refs/tags/v0.1.1.tar.gz"
  sha256 "f045e828bf3cd4d7a26c6ec7c1ff2ae2656daa014b0c80bc8f5011af2d709aaa"
  license "MIT"
  depends_on "python@3.14"

  def install
    libexec.install "brew2fink"
    (bin/"brew2fink").write <<~EOS
      #!/bin/sh
      export PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}"
      exec "#{Formula["python@3.14"].opt_bin}/python3.14" -m brew2fink "$@"
    EOS
    chmod 0755, bin/"brew2fink"
  end

  test do
    system bin/"brew2fink", "--help"
  end
end
