class Brew2fink < Formula
  desc "Safe Homebrew to Fink migration planner"
  homepage "https://github.com/tomck/homebrew-brew2fink"
  url "https://github.com/tomck/homebrew-brew2fink/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "916282cac6fc432b5045d01597d67afefbc7ea561a97c5ce6d70e2a5d9067447"
  license "MIT"
  depends_on "python@3.14"

  def install
    libexec.install "brew2fink"
    (bin/"brew2fink").write <<~EOS
      #!/bin/sh
      export PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}"
      exec "#{Formula[\"python@3.14\"].opt_bin}/python3.14" -m brew2fink "$@"
    EOS
    chmod 0755, bin/"brew2fink"
  end

  test do
    system bin/"brew2fink", "--help"
  end
end
