class Brew2fink < Formula
  desc "Safe Homebrew to Fink migration planner"
  homepage "https://github.com/tomck/brew2fink"
  url "https://github.com/tomck/brew2fink/archive/refs/tags/v0.1.1.tar.gz"
  sha256 "ddc4918a07f3537c0d43ccbed70992aef404b1a3c2646b63d6be064679af4eaf"
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
