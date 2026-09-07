class MacpkgMigrate < Formula
  desc "Safe multi-manager Homebrew, MacPorts, and Fink migration planner"
  homepage "https://github.com/tomck/macpkg-migrate"
  url "https://github.com/tomck/macpkg-migrate/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "79b0b82e2e33b954ee100a7b4ead8f5fedd0ddcf38b5859b78bb6e21d62f5c75"
  license "MIT"
  depends_on "python@3.14"

  def install
    libexec.install "macpkg_migrate", "pyproject.toml", "README.md"
    (bin/"macpkg-migrate").write <<~EOS
      #!/bin/sh
      export PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}"
      exec "#{Formula["python@3.14"].opt_bin}/python3.14" -m macpkg_migrate "$@"
    EOS
    chmod 0755, bin/"macpkg-migrate"
  end

  test do
    system bin/"macpkg-migrate", "--help"
  end
end
